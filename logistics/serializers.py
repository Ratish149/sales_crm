from rest_framework import serializers

from .models import Logistics


class LogisticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Logistics
        fields = "__all__"
