from rest_framework import serializers

from .models import TawkTo


class TawkToSerializer(serializers.ModelSerializer):
    class Meta:
        model = TawkTo
        fields = "__all__"
