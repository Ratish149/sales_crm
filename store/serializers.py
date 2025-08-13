from rest_framework import serializers
from .models import SiteModel

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteModel
        fields = '__all__'
