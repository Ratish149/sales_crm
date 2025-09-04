from rest_framework import serializers
from .models import Client, Domain
from accounts.serializers import CustomUserSerializer


class ClientSerializer(serializers.ModelSerializer):
    owner = CustomUserSerializer(read_only=True)

    class Meta:
        model = Client
        fields = '__all__'


class DomainSerializer(serializers.ModelSerializer):
    tenant = ClientSerializer(read_only=True)

    class Meta:
        model = Domain
        fields = '__all__'
