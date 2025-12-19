from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .models import Customer


class CustomerJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        """
        Attempts to find and return a Customer using the given validated token.
        """
        try:
            user_id = validated_token.get("user_id")
        except KeyError:
            return None

        if not user_id:
            return None

        try:
            customer = Customer.objects.get(id=user_id)
        except Customer.DoesNotExist:
            raise AuthenticationFailed("Customer not found", code="user_not_found")

        # Add is_authenticated property if not present (though Customer model doesn't inherit from AbstractBaseUser)
        # DRF check request.user.is_authenticated
        return customer
