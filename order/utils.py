import os

import requests
from django.utils import timezone
from dotenv import load_dotenv
from rest_framework.response import Response

from logistics.models import Logistics
from logistics.views import dash_login
from order.models import Order, OrderItem

load_dotenv()


def send_order_to_dash(order):
    """
    Send order details to Dash logistics service.

    Args:
        order: Order instance to be sent to Dash

    Returns:
        Response: API response with success/error details
    """
    DASH_BASE_URL = os.getenv("DASH_BASE_URL")
    dash_obj = Logistics.objects.filter(is_enabled=True, logistic="Dash").first()
    print(dash_obj)

    if not dash_obj:
        return Response(
            {"error": "No active and enabled Dash logistics configuration found"},
            status=400,
        )

    # Handle token expiry
    token_expired = dash_obj.expires_at and dash_obj.expires_at <= timezone.now()
    if not dash_obj.access_token or token_expired:
        dash_obj.access_token = None
        dash_obj.refresh_token = None
        dash_obj.expires_at = None

        try:
            dash_obj.save()
            dash_obj, error = dash_login(
                dash_obj.email, dash_obj.password, dash_obj=dash_obj
            )
            if not dash_obj:
                return Response(
                    {"error": "Failed to refresh Dash token", "details": error},
                    status=400,
                )
            dash_obj.refresh_from_db()
        except Exception as e:
            return Response(
                {"error": f"Exception during Dash login: {str(e)}"}, status=500
            )

    access_token = dash_obj.access_token
    DASH_API_URL = f"{DASH_BASE_URL}/api/v1/clientOrder/add-order"
    HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        order = Order.objects.get(id=order.id)
    except Order.DoesNotExist:
        return Response(
            {"error": f"Order with id {order.id} does not exist."}, status=404
        )

    order_products = OrderItem.objects.filter(order=order)

    # Build product list
    product_name_list = []
    for op in order_products:
        try:
            if op.variant and hasattr(op.variant, "product"):
                product_name = op.variant.product.name
            elif op.product:
                product_name = op.product.name
            else:
                product_name = "Unknown Product"
            product_name_list.append(f"{op.quantity}x {product_name}")
        except Exception:
            continue

    product_name = ", ".join(product_name_list) if product_name_list else "No products"
    product_price = order.total_amount
    full_address = getattr(order, "shipping_address", "No address provided")

    # Map payment type
    payment_type = (
        order.payment_type.lower() if order.payment_type else "cashOnDelivery"
    )
    if payment_type in ["cod", "cash_on_delivery"]:
        payment_type = "cashOnDelivery"
    elif payment_type in ["khalti", "esewa"]:
        payment_type = "prepaid"
    else:
        payment_type = "cashOnDelivery"

    receiver_location = getattr(order, "city", None) or "Kathmandu"

    # Remove +977 or 977 prefix from phone numbers if present
    def clean_phone_number(phone):
        if not phone:
            return ""
        phone = str(phone).strip()
        if phone.startswith("+977"):
            return phone[4:]
        elif phone.startswith("977"):
            return phone[3:]
        return phone

    customer = {
        "receiver_name": order.customer_name,
        "receiver_contact": clean_phone_number(order.customer_phone),
        "receiver_alternate_number": "",
        "receiver_address": full_address,
        "receiver_location": receiver_location,
        "payment_type": payment_type,
        "product_name": product_name,
        "client_note": "",
        "receiver_landmark": getattr(order, "landmark", "") or "",
        "order_reference_id": str(order.order_number),
        "product_price": float(product_price) if product_price is not None else 0.0,
    }

    payload = {"customers": [customer]}
    print(payload)

    try:
        dash_response = requests.post(
            DASH_API_URL, json=payload, headers=HEADERS, timeout=30
        )
        print(dash_response)

        try:
            response_data = dash_response.json()
        except ValueError:
            return Response(
                {
                    "error": "Invalid JSON response from Dash",
                    "status_code": dash_response.status_code,
                    "response_text": dash_response.text,
                },
                status=500,
            )

        if dash_response.status_code != 200 or response_data.get("status") != "success":
            return Response(
                {
                    "error": "Failed to send order to Dash",
                    "dash_response": response_data,
                },
                status=dash_response.status_code or 500,
            )

        tracking_codes = []
        if response_data.get("data", {}).get("detail"):
            tracking_codes = [
                {
                    "tracking_code": item.get("tracking_code"),
                    "order_reference_id": item.get("order_reference_id"),
                }
                for item in response_data["data"]["detail"]
            ]

        # ✅ Only update status if success & tracking code exists
        result = {
            "success": False,
            "tracking_codes": tracking_codes,
            "dash_response": response_data,
        }

        if tracking_codes:
            order.dash_tracking_code = tracking_codes[0]["tracking_code"]
            order.status = "shipped"
            order.save(update_fields=["dash_tracking_code", "status"])
            result["success"] = True

        return Response(
            {
                "message": "Order sent to Dash successfully.",
                **result,
            },
            status=200,
        )

    except requests.exceptions.RequestException as e:
        return Response(
            {"error": "Failed to connect to Dash API", "details": str(e)},
            status=500,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return Response(
            {"error": "An unexpected error occurred", "details": str(e)}, status=500
        )
