from rest_framework import serializers

from .models import MSClarity


class MSClaritySerializer(serializers.ModelSerializer):
    class Meta:
        model = MSClarity
        fields = "__all__"
