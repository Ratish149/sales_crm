from rest_framework import serializers
from .models import Invitation, CustomUser, StoreProfile
import cloudinary
import cloudinary.uploader
import os

CLOUDINARY_CLOUD_NAME = "dlqqwdj0o"
CLOUDINARY_API_KEY = "191929385875364"
CLOUDINARY_API_SECRET = "zsPz35zRKIoFHrC1tEQFhe3_Z9U"

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
            validated_data['store'] = request.user.store
        return super().create(validated_data)


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        try:
            invitation = Invitation.objects.get(
                token=data['token'], accepted=False)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid or expired invitation token.")
        data['invitation'] = invitation
        return data

    def create(self, validated_data):
        invitation = validated_data['invitation']
        password = validated_data['password']
        # Create the user
        user = CustomUser.objects.create_user(
            email=invitation.email,
            password=password,
            role=invitation.role,
            store=invitation.store,
            username=invitation.email  # or generate a username
        )
        invitation.accepted = True
        invitation.save()
        return user


class StoreProfileSerializer(serializers.ModelSerializer):
    logo_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = StoreProfile
        fields = ['id', 'store_name', 'store_address', 'store_number', 'logo_file', 'logo',
                  'business_category', 'facebook_url', 'instagram_url', 'twitter_url', 'tiktok_url', 'whatsapp_number']
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
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
