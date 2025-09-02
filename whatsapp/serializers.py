from rest_framework import serializers
from .models import Whatsapp


class WhatsappSerializer(serializers.ModelSerializer):
    class Meta:
        model = Whatsapp
        fields = '__all__'
