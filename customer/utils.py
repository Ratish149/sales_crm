from customer.authentication import CustomerJWTAuthentication


def get_customer_from_request(request):
    """
    Returns Customer instance from JWT token if present.
    Returns None if no token is provided.
    Raises AuthenticationFailed if token is present but invalid.
    """
    auth = CustomerJWTAuthentication()
    try:
        user_auth_tuple = auth.authenticate(request)
        if user_auth_tuple is None:
            return None
        return user_auth_tuple[0]
    except Exception:
        return None
