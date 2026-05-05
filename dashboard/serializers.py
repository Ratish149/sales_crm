from rest_framework import serializers

from accounts.models import CustomUser, UserActivity
from tenants.models import Client


class RecentUserSerializer(serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()
    paid_until = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "username",
            "role",
            "date_joined",
            "created_at",
            "plan_name",
            "store_name",
            "paid_until",
        )

    def get_plan_name(self, obj):
        try:
            # Client has owner = OneToOneField(CustomUser)
            client = Client.objects.get(owner=obj)
            return client.pricing_plan.name if client.pricing_plan else "No Plan"
        except Client.DoesNotExist:
            return "No Plan"

    def get_store_name(self, obj):
        try:
            client = Client.objects.get(owner=obj)
            return client.name
        except Client.DoesNotExist:
            return "No Store"

    def get_paid_until(self, obj):
        try:
            client = Client.objects.get(owner=obj)
            return client.paid_until
        except Client.DoesNotExist:
            return None


class UserActivityDashboardSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    website_type = serializers.CharField(source="user.website_type", read_only=True)

    class Meta:
        model = UserActivity
        fields = (
            "id",
            "user_email",
            "first_name",
            "last_name",
            "website_type",
            "action",
            "description",
            "timestamp",
            "metadata",
        )
