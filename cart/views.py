from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.filters import CartFilter
from cart.selectors.cart_selector import get_cart_by_id, get_optimized_cart_queryset
from cart.serializers import (
    AdminCartListSerializer,
    CartContactUpdateSerializer,
    CartItemAddSerializer,
    CartSerializer,
)
from cart.services import cart_service
from customer.utils import get_customer_from_request
from sales_crm.authentication import TenantJWTAuthentication


class CustomCartPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


class MyActiveCartAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        customer = get_customer_from_request(request)
        if not customer:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        cart_service.sweep_abandoned_carts(idle_minutes=1440)
        cart = cart_service.create_cart(customer=customer)
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class CartCreateAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        customer = get_customer_from_request(request)
        contact_name = request.data.get("contact_name", "")
        contact_phone = request.data.get("contact_phone", "")
        contact_email = request.data.get("contact_email", "")

        cart = cart_service.create_cart(
            customer=customer,
            contact_name=contact_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
        )
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)


class CartDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk, *args, **kwargs):
        cart_service.sweep_abandoned_carts(idle_minutes=1440)
        cart = get_cart_by_id(pk)
        if not cart:
            return Response(
                {"detail": "Cart not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        customer = get_customer_from_request(request)
        if customer:
            cart = cart_service.associate_cart_with_customer(cart, customer)

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class CartItemAddAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk, *args, **kwargs):
        cart = get_cart_by_id(pk)
        if not cart:
            return Response(
                {"detail": "Cart not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        customer = get_customer_from_request(request)
        if customer:
            cart = cart_service.associate_cart_with_customer(cart, customer)

        serializer = CartItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_obj = serializer.validated_data.get("product_obj")
        variant_obj = serializer.validated_data.get("variant_obj")
        quantity = serializer.validated_data.get("quantity", 1)
        price = serializer.validated_data.get("price")

        cart_service.add_or_update_cart_item(
            cart=cart,
            product=product_obj,
            variant=variant_obj,
            quantity=quantity,
            price=price,
        )
        updated_cart = get_cart_by_id(pk)
        return Response(CartSerializer(updated_cart).data, status=status.HTTP_200_OK)


class CartItemDeleteAPIView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk, item_id, *args, **kwargs):
        cart = get_cart_by_id(pk)
        if not cart:
            return Response(
                {"detail": "Cart not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        success = cart_service.remove_cart_item(cart, item_id)
        if not success:
            return Response(
                {"detail": "Cart item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        updated_cart = get_cart_by_id(pk)
        return Response(CartSerializer(updated_cart).data, status=status.HTTP_200_OK)


class CartContactUpdateAPIView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, pk, *args, **kwargs):
        cart = get_cart_by_id(pk)
        if not cart:
            return Response(
                {"detail": "Cart not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CartContactUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        cart_service.update_cart_contact(
            cart=cart,
            contact_name=serializer.validated_data.get("contact_name"),
            contact_phone=serializer.validated_data.get("contact_phone"),
            contact_email=serializer.validated_data.get("contact_email"),
        )
        updated_cart = get_cart_by_id(pk)
        return Response(CartSerializer(updated_cart).data, status=status.HTTP_200_OK)


class AdminCartListAPIView(generics.ListAPIView):
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = AdminCartListSerializer
    pagination_class = CustomCartPagination
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        django_filters.DjangoFilterBackend,
    ]
    search_fields = ["contact_name", "contact_phone", "contact_email"]
    ordering_fields = ["created_at", "last_activity_at", "status"]
    filterset_class = CartFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return get_optimized_cart_queryset().none()
        # Automatically mark active carts idle for 1 day (1440 minutes) as ABANDONED
        cart_service.sweep_abandoned_carts(idle_minutes=1440)
        return get_optimized_cart_queryset()


class CartSweepAbandonedAPIView(APIView):
    authentication_classes = [TenantJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        idle_minutes = int(request.data.get("idle_minutes", 45))
        count = cart_service.sweep_abandoned_carts(idle_minutes=idle_minutes)
        return Response(
            {
                "detail": f"Successfully marked {count} stale cart(s) as abandoned.",
                "abandoned_count": count,
            },
            status=status.HTTP_200_OK,
        )
