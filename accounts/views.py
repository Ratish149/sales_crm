from .serializers import AcceptInvitationSerializer, InvitationSerializer
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import CustomUser
from allauth.account.utils import send_email_confirmation
import os
import resend
from django.template.loader import render_to_string
from dotenv import load_dotenv
load_dotenv()
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


class InvitationCreateView(generics.CreateAPIView):
    serializer_class = InvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):

        resend.api_key = os.getenv("RESEND_API_KEY")
        invitation = serializer.save()
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        invite_url = f"{FRONTEND_URL}/user/invite/{invitation.token}"
        # Prepare email content using a template
        html_body = render_to_string(
            "account/email/invitation_message.html",
            {"store_name": invitation.store.store_name,
                "role": invitation.role, "invite_url": invite_url}
        )
        params = {
            "from": "sales@baliyoventures.com",
            "to": [invitation.email],
            "subject": f"You are invited by {invitation.invited_by.email} to join {invitation.store.store_name}!",
            "html": html_body,
        }
        try:
            response = resend.Emails.send(params)
            print(f"Invitation email sent successfully: {response}")
        except Exception as e:
            print(f"Error sending invitation email: {e}")


class AcceptInvitationView(APIView):
    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'detail': 'User created successfully.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
