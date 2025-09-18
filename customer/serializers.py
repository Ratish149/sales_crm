from rest_framework import serializers
from .models import Customer


class CustomerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Customer
        fields = ["id", "first_name", "last_name",
                  "email", "phone", "address", "password"]

    def create(self, validated_data):
        # password will be hashed in model's save()
        return Customer.objects.create(**validated_data)


class CustomerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
