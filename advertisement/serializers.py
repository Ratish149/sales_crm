from rest_framework import serializers
from .models import PopUp, PopUpForm


class PopUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = PopUp
        fields = '__all__'


class PopUpFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = PopUpForm
        fields = '__all__'
