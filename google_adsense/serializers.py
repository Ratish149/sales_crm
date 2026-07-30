from rest_framework import serializers

from .models import GoogleAdSense


class GoogleAdSenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleAdSense
        fields = "__all__"
