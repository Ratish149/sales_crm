import time
import boto3
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import FileUploadSerializer, FileDeleteSerializer

class S3UploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file_obj = serializer.validated_data['file']
            tenant_name = request.tenant.schema_name if hasattr(request, 'tenant') and request.tenant else 'public'
            
            # Sanitize filename and add timestamp
            timestamp = int(time.time() * 1000)
            file_name = f"{timestamp}-{file_obj.name.replace(' ', '_')}"
            
            # Construct S3 object key
            s3_key = f"public/nepdora/tenant/{tenant_name}/{file_name}"
            
            s3 = boto3.client(
                's3',
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            
            try:
                # Explicitly create folder if it doesn't exist (helpful for some S3 clients like DO Spaces)
                folder_prefix = f"public/nepdora/tenant/{tenant_name}/"
                result = s3.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix=folder_prefix, MaxKeys=1)
                if 'Contents' not in result:
                    s3.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=folder_prefix)
                
                s3.upload_fileobj(
                    file_obj,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    s3_key,
                    ExtraArgs={
                        'ACL': 'public-read',
                        'ContentType': file_obj.content_type
                    }
                )
                
                # Construct the URL
                if settings.AWS_S3_CUSTOM_DOMAIN:
                    file_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{s3_key}"
                else:
                    file_url = f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{s3_key}"
                    
                return Response({'url': file_url}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class S3DeleteView(APIView):

    def delete(self, request, *args, **kwargs):
        # Support both body payload and query params (useful if frontend tool drops body on DELETE)
        data = request.data if request.data else request.query_params
        serializer = FileDeleteSerializer(data=data)
        if serializer.is_valid():
            urls = serializer.validated_data.get('urls', [])
            
            keys_to_delete = []
            
            def extract_key(u):
                if settings.AWS_S3_CUSTOM_DOMAIN:
                    prefix = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/"
                else:
                    prefix = f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/"
                if u.startswith(prefix):
                    return u[len(prefix):]
                return None
                
            for u in urls:
                key = extract_key(u)
                if key: keys_to_delete.append(key)
                
            if not keys_to_delete:
                return Response({'error': 'No valid URLs provided.'}, status=status.HTTP_400_BAD_REQUEST)
            
            s3 = boto3.client(
                's3',
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            
            try:
                delete_objects = [{'Key': k} for k in set(keys_to_delete)] # use set to avoid duplicates
                
                # S3 allows up to 1000 objects per delete request
                for i in range(0, len(delete_objects), 1000):
                    batch = delete_objects[i:i + 1000]
                    if batch:
                        s3.delete_objects(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Delete={'Objects': batch, 'Quiet': True}
                        )
                return Response({'message': f'Successfully deleted {len(delete_objects)} files.'}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class S3ListView(APIView):
    def get(self, request, *args, **kwargs):
        tenant_name = request.tenant.schema_name if hasattr(request, 'tenant') and request.tenant else 'public'
        prefix = f"public/nepdora/tenant/{tenant_name}/"
        
        s3 = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        
        try:
            response = s3.list_objects_v2(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    
                    # Skip S3 folder marker objects (they end with '/')
                    if key.endswith('/'):
                        continue
                        
                    if settings.AWS_S3_CUSTOM_DOMAIN:
                        url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{key}"
                    else:
                        url = f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{key}"
                        
                    files.append({
                        'name': key.split('/')[-1],
                        'url': url,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
                    
            return Response({'files': files}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class S3DeleteFolderView(APIView):
    def delete(self, request, *args, **kwargs):
        tenant_name = request.tenant.schema_name if hasattr(request, 'tenant') and request.tenant else 'public'
        prefix = f"public/nepdora/tenant/{tenant_name}/"
        
        s3 = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        
        try:
            # List all objects in the folder
            objects_to_delete = s3.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix=prefix)
            
            if 'Contents' in objects_to_delete:
                delete_keys = [{'Key': obj['Key']} for obj in objects_to_delete['Contents']]
                
                # Delete objects in bulk (up to 1000 per call, handles typical folder size)
                s3.delete_objects(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Delete={
                        'Objects': delete_keys,
                        'Quiet': True
                    }
                )
                
            return Response({'message': 'Folder and all its contents deleted successfully.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
