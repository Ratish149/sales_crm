from rest_framework import serializers

from accounts.serializers import CustomUserSerializer

from .models import Client, Domain


class ClientSerializer(serializers.ModelSerializer):
    owner = CustomUserSerializer(read_only=True)

    class Meta:
        model = Client
        fields = "__all__"


class DomainSerializer(serializers.ModelSerializer):
    tenant = ClientSerializer(read_only=True)

    class Meta:
        model = Domain
        fields = "__all__"


class TemplateTenantSerializer(serializers.ModelSerializer):
    domains = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "schema_name",
            "owner_id",
            "created_on",
            "paid_until",
            "template_image",
            "is_template_account",
            "domains",
        ]

    def get_domains(self, obj):
        domains = Domain.objects.filter(tenant=obj)
        return [domain.domain for domain in domains]
