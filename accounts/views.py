from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CustomUser
from allauth.account.utils import send_email_confirmation
from django.core.exceptions import ObjectDoesNotExist
# Create your views here.


class ChangePasswordView(APIView):
    def post(self, request):
        password = request.data.get('password')
        email = request.data.get('email')
        user = CustomUser.objects.get(email=email)
        user.set_password(password)
        user.save()
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)


class ResendEmailVerificationView(APIView):
    def post(self, request):
        email = request.data.get('email')
        user = CustomUser.objects.get(email=email)
        if user.is_authenticated and not user.emailaddress_set.filter(verified=True).exists():
            send_email_confirmation(request, user)
            return Response({"detail": "Verification email sent."})
        return Response({"detail": "Already verified or not authenticated."}, status=status.HTTP_400_BAD_REQUEST)

