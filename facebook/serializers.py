from rest_framework import serializers

from .models import Facebook


class FacebookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facebook
        fields = "__all__"
