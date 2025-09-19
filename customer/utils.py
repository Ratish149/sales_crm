from rest_framework_simplejwt.authentication import JWTAuthentication
from customer.models import Customer


def get_customer_from_request(request):
    """
    Returns Customer instance from JWT token if present.
    Returns None if no token is provided.
    Raises AuthenticationFailed if token is present but invalid.
    """
    auth = JWTAuthentication()
    header = auth.get_header(request)
    if header is None:
        return None  # No token, return None

    raw_token = auth.get_raw_token(header)
    if raw_token is None:
        return None

    validated_token = auth.get_validated_token(raw_token)
    customer_id = validated_token.get("user_id")
    if not customer_id:
        return None

    customer = Customer.objects.filter(id=customer_id).first()
    return customer
