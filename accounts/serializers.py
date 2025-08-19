from rest_framework import serializers
from .models import Invitation, CustomUser, StoreProfile
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv
load_dotenv()

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ['id', 'email', 'store', 'role',
                  'token', 'accepted', 'created_at']
        read_only_fields = ['id', 'token', 'accepted', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['invited_by'] = request.user
        return super().create(validated_data)


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        try:
            invitation = Invitation.objects.get(
                token=data['token'],
                accepted=False
            )
            # Check if user with this email already exists
            if CustomUser.objects.filter(email=invitation.email).exists():
                raise serializers.ValidationError(
                    "A user with this email already exists. Please log in instead."
                )
            data['invitation'] = invitation
            return data
        except Invitation.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid or expired invitation token."
            )

    def create(self, validated_data):
        invitation = validated_data['invitation']
        password = validated_data['password']

        # Create the user
        user = CustomUser.objects.create_user(
            email=invitation.email,
            password=password,
            role=invitation.role,
            username=invitation.email,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', '')
        )

        # Accept the invitation (this will add user to store and handle roles)
        invitation.accept(user)

        return user


class StoreProfileSerializer(serializers.ModelSerializer):

    logo_file = serializers.FileField(write_only=True, required=False)
    document_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = StoreProfile
        fields = ['id', 'store_name', 'store_address', 'store_number', 'logo_file', 'logo',
                  'business_category', 'facebook_url', 'instagram_url', 'twitter_url', 'tiktok_url', 'whatsapp_number', 'document_url', 'document_file']
        read_only_fields = ['logo']

    def create(self, validated_data):
        logo_file = validated_data.pop('logo_file', None)
        if logo_file:
            upload_result = cloudinary.uploader.upload(
                logo_file,
                folder=f"store_logos",
                public_id=f"store_logo_{validated_data['store_name']}",
                overwrite=True,
                resource_type="image"
            )
            validated_data['logo'] = upload_result['secure_url']
        return super().create(validated_data)

    def update(self, instance, validated_data):
        logo_file = validated_data.pop('logo_file', None)
        if logo_file:
            upload_result = cloudinary.uploader.upload(
                logo_file,
                folder=f"store_logos",
                public_id=f"store_logo_{instance.store_name}",
                overwrite=True,
                resource_type="image"
            )
            validated_data['logo'] = upload_result['secure_url']
        document_file = validated_data.pop('document_file', None)
        if document_file:
            upload_result = cloudinary.uploader.upload(
                document_file,
                folder=f"kyc_documents",
                public_id=f"kyc_document_{instance.store_name}",
                overwrite=True,
                resource_type="raw"
            )
            validated_data['document_url'] = upload_result['secure_url']
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
