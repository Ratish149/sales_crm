# Create your views here.

from datetime import timedelta

import requests
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response

from .models import Logistics
from .serializers import LogisticsSerializer

DASH_BASE_URL = "https://dashlogistics.com.np"


def dash_login(email, password, dash_obj=None):
    # Use values from dash_obj if provided, else use defaults
    client_id = dash_obj.client_id
    client_secret = dash_obj.client_secret
    grant_type = dash_obj.grant_type
    is_enabled = dash_obj.is_enabled
    DASH_LOGIN_URL = f"{DASH_BASE_URL}/api/v1/login/client/"
    body = {
        "clientId": client_id,
        "clientSecret": client_secret,
        "grantType": grant_type,
        "email": email,
        "password": password,
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        response = requests.post(DASH_LOGIN_URL, json=body, headers=headers)
        if response.status_code == 200:
            data = response.json().get("data", {})
            access_token = data.get("accessToken")
            refresh_token = data.get("refreshToken")
            expires_in = data.get("expiresIn")
            expires_at = (
                timezone.now() + timedelta(seconds=expires_in) if expires_in else None
            )
            dash_defaults = {
                "email": email,
                "password": password,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": grant_type,
                "is_enabled": is_enabled,
            }
            dash_obj_db, created = Logistics.objects.update_or_create(
                logistic=dash_obj.logistic,
                defaults=dash_defaults,
            )
            return dash_obj_db, None
        elif response.status_code == 422:
            return None, response.json()
        else:
            return None, {
                "error": "Failed to login to Dash",
                "details": response.text,
                "status": response.status_code,
            }
    except requests.RequestException as e:
        return None, {"error": "Failed to login to Dash", "details": str(e)}


class LogisticsListCreateView(generics.ListCreateAPIView):
    queryset = Logistics.objects.all()
    serializer_class = LogisticsSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get the validated data
        validated_data = serializer.validated_data

        # Check if this is a Dash logistics
        if validated_data.get("logistic") == "Dash":
            # Create a temporary instance for login
            dash_obj = Logistics(**validated_data)

            # Attempt to login
            result, error = dash_login(
                email=validated_data["email"],
                password=validated_data["password"],
                dash_obj=dash_obj,
            )

            if error:
                return Response(
                    {"error": "Failed to authenticate with Dash", "details": error},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # If login successful, the instance is already saved by dash_login
            headers = self.get_success_headers(serializer.data)
            return Response(
                self.serializer_class(result).data,
                status=status.HTTP_201_CREATED,
                headers=headers,
            )

        # For non-Dash logistics, save normally
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class LogisticsRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Logistics.objects.all()
    serializer_class = LogisticsSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Get the validated data
        validated_data = serializer.validated_data

        # Check if this is a Dash logistics update with credentials
        if instance.logistic == "Dash" and any(
            field in validated_data for field in ["email", "password"]
        ):
            # Create a temporary instance with updated data
            temp_data = {**serializer.data, **validated_data}
            dash_obj = Logistics(**temp_data)

            # If password is being updated, we need to use the new one for login
            password = validated_data.get("password", instance.password)

            # Attempt to login with the new credentials
            result, error = dash_login(
                email=validated_data.get("email", instance.email),
                password=password,
                dash_obj=dash_obj,
            )

            if error:
                return Response(
                    {"error": "Failed to authenticate with Dash", "details": error},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # If login successful, the instance is already saved by dash_login
            return Response(self.serializer_class(result).data)

        # For non-credential updates or non-Dash logistics, update normally
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)
