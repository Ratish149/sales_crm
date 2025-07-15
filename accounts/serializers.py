from rest_framework import serializers
from .models import Invitation, CustomUser


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
