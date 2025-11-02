from rest_framework import serializers

from .models import GoogleAnalytic


class GoogleAnalyticSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleAnalytic
        fields = "__all__"
