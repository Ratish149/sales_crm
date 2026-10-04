import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.conf import settings
from django.db.models import Q
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.response import Response

from logistics.models import Logistics
from order.models import Order
from tenants.models import Client

logger = logging.getLogger(__name__)


def clean_phone_number(phone: Optional[str]) -> str:
    """
    Cleans phone number by stripping whitespace, hyphens, and Nepal country code (+977 or 977).
    """
    if not phone:
        return ""
    phone_str = str(phone).strip().replace(" ", "").replace("-", "")
    if phone_str.startswith("+977"):
        return phone_str[4:]
    elif phone_str.startswith("977"):
        return phone_str[3:]
    return phone_str


def get_ncm_credentials(
    logistic_obj: Optional[Logistics] = None,
) -> Tuple[Optional[str], str, Optional[Logistics]]:
    """
    Retrieves NCM API token (from Logistics.api_key only), base URL, and Logistics model instance.
    """
    ncm_base_url = getattr(
        settings,
        "NCM_BASE_URL",
        os.getenv("NCM_BASE_URL", "https://demo.nepalcanmove.com"),
    )

    if not logistic_obj:
        logistic_obj = Logistics.objects.filter(logistic="NCM", is_enabled=True).first()

    token = getattr(logistic_obj, "api_key", None) if logistic_obj else None

    return token, ncm_base_url, logistic_obj


def call_ncm_order_api(
    payload: Dict[str, Any], token: str, base_url: str
) -> Tuple[int, Dict[str, Any]]:
    """
    Makes the HTTP POST request to NCM API endpoint: /api/v1/order/create
    """
    create_url = f"{base_url.rstrip('/')}/api/v1/order/create"
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }

    # Ensure all payload values are properly typed strings/formatted
    formatted_payload = {
        str(k): ("" if v is None else str(v).strip()) for k, v in payload.items()
    }

    try:
        payload_str = json.dumps(formatted_payload, indent=4, ensure_ascii=False)
    except Exception:
        payload_str = str(formatted_payload)

    print("================== NCM REQUEST ==================")
    print(f"URL: {create_url}")
    print("Payload:")
    print(payload_str)
    print("==================================================")

    try:
        response = requests.post(
            create_url,
            json=formatted_payload,
            headers=headers,
            timeout=30,
        )

        try:
            response_data = response.json()
            response_str = json.dumps(response_data, indent=4, ensure_ascii=False)
            print(f"NCM Response [{response.status_code}]:\n{response_str}")
        except ValueError:
            print(f"NCM Response [{response.status_code}]: {response.text}")
            return response.status_code or 502, {
                "error": "Invalid JSON response from NCM API",
                "status_code": response.status_code,
                "response_text": response.text,
            }

        return response.status_code, response_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to communicate with NCM API: {e}")
        return 502, {
            "error": "Failed to connect to NCM API",
            "details": str(e),
        }


def send_order_to_ncm(
    order: Order,
    extra_data: Optional[Dict[str, Any]] = None,
    logistic_obj: Optional[Logistics] = None,
) -> Response:
    """
    Business service to send an existing order to Nepal Can Move (NCM).

    Args:
        order: Order instance to be sent to NCM.
        extra_data: Optional dictionary containing request overrides (e.g. fbranch, branch, weight).
        logistic_obj: Optional Logistics model instance.

    Returns:
        DRF Response instance with appropriate HTTP status code.
    """
    extra_data = extra_data or {}

    # Check logistics active status
    if logistic_obj and not logistic_obj.is_enabled:
        return Response(
            {"error": "NCM logistics configuration is not enabled"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token, ncm_base_url, logistic_obj = get_ncm_credentials(logistic_obj)
    if not token:
        return Response(
            {
                "error": "NCM access token is not configured in Logistics (api_key required)."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 1. Customer Name
    name = (extra_data.get("name") or order.customer_name or "").strip()

    # 2. Customer Phone
    phone = clean_phone_number(extra_data.get("phone") or order.customer_phone)

    # 3. Secondary Phone (optional)
    phone2 = clean_phone_number(extra_data.get("phone2", ""))

    # 4. COD Amount (cod_charge)
    is_order_paid = getattr(order, "is_paid", False) is True or str(
        extra_data.get("is_paid", "")
    ).lower() in ["true", "1", "yes"]
    if is_order_paid:
        cod_charge = "0"
    elif (
        extra_data.get("cod_charge") is not None
        and str(extra_data.get("cod_charge")).strip() != ""
    ):
        cod_charge = str(extra_data["cod_charge"]).strip()
    elif order.payment_type == "split":
        cash_amount = getattr(order, "cash_amount", 0) or 0
        cod_charge = (
            str(int(cash_amount))
            if float(cash_amount).is_integer()
            else str(cash_amount)
        )
    elif order.payment_type in ["cod", "cash_on_delivery", "cash", None]:
        total = getattr(order, "total_amount", 0) or 0
        cod_charge = str(int(total)) if float(total).is_integer() else str(total)
    else:
        # Pre-paid online payments (e.g. khalti, esewa)
        cod_charge = "0"

    # 5. Customer Address
    address = (
        extra_data.get("address")
        or order.shipping_address
        or order.customer_address
        or ""
    ).strip()

    # 6. From Branch (Origin Branch - required)
    # Check extra_data, or Logistics.branch, or Logistics.client_secret
    logistics_from_branch = None
    if logistic_obj:
        logistics_from_branch = getattr(logistic_obj, "branch", None) or getattr(
            logistic_obj, "client_secret", None
        )

    fbranch = extra_data.get("fbranch") or logistics_from_branch or ""
    fbranch = str(fbranch).strip() if fbranch else ""

    # 7. Destination Branch (required)
    destination_branch = (
        extra_data.get("branch")
        or extra_data.get("location_name")
        or extra_data.get("location")
        or getattr(order, "city", "")
        or ""
    )
    branch = str(destination_branch).strip() if destination_branch else ""

    # 8. Package Name / Description (optional)
    if extra_data.get("package"):
        package = str(extra_data["package"]).strip()
    else:
        product_names = []
        for item in order.items.select_related("product", "variant__product").all():
            p_name = ""
            if item.variant and item.variant.product:
                p_name = item.variant.product.name
            elif item.product:
                p_name = item.product.name
            if p_name:
                product_names.append(f"{item.quantity}x {p_name}")
        package = ", ".join(product_names) if product_names else "Package"

    # 9. Vendor Reference ID (optional)
    vref_id = str(
        extra_data.get("vref_id") or order.order_number or str(order.id)
    ).strip()

    # 10. Delivery Instruction (optional)
    instruction = str(
        extra_data.get("instruction") or getattr(order, "note", "") or ""
    ).strip()

    # 11. Delivery Type (optional: Door2Door, Branch2Door, Branch2Branch, Door2Branch)
    delivery_type = str(extra_data.get("delivery_type") or "Door2Door").strip()

    # 12. Weight (optional, default: 1 kg)
    weight = str(extra_data.get("weight") or "1").strip()

    # Validate required fields against NCM documentation
    validation_errors = {}
    if not name:
        validation_errors["name"] = "Invalid Name"
    if not phone:
        validation_errors["phone"] = "Invalid Phone Number"
    if cod_charge == "" or cod_charge is None:
        validation_errors["cod_charge"] = "Invalid COD Amount"
    if not address:
        validation_errors["address"] = "Invalid Address"
    if not fbranch:
        validation_errors["fbranch"] = (
            "From branch (fbranch) is required. Set branch or client_secret in Logistics, or provide fbranch in request."
        )
    if not branch:
        validation_errors["branch"] = "Invalid Branch"

    if validation_errors:
        return Response(
            {"Error": validation_errors}, status=status.HTTP_400_BAD_REQUEST
        )

    payload = {
        "name": name,
        "phone": phone,
        "phone2": phone2,
        "cod_charge": str(cod_charge),
        "address": address,
        "fbranch": fbranch,
        "branch": branch,
        "package": package,
        "vref_id": vref_id,
        "instruction": instruction,
        "delivery_type": delivery_type,
        "weight": str(weight),
    }

    status_code, response_data = call_ncm_order_api(payload, token, ncm_base_url)

    if status_code == 200 and "orderid" in response_data:
        old_status = order.status
        order.status = "shipped"
        update_fields = ["status"]

        if hasattr(order, "ncm_order_id"):
            order.ncm_order_id = str(response_data.get("orderid"))
            update_fields.append("ncm_order_id")

        try:
            order.save(update_fields=update_fields)
        except Exception:
            order.save(update_fields=["status"])

        if old_status == "pending":
            order.deduct_stock()

        return Response(response_data, status=status.HTTP_200_OK)

    return Response(
        response_data,
        status=status_code
        if status_code in [400, 401, 403, 404, 422, 500, 502]
        else status.HTTP_400_BAD_REQUEST,
    )


def create_direct_ncm_order(
    validated_data: Dict[str, Any],
    logistic_obj: Optional[Logistics] = None,
) -> Response:
    """
    Directly creates an order in Nepal Can Move without requiring an existing Order instance.
    """
    token, ncm_base_url, logistic_obj = get_ncm_credentials(logistic_obj)
    if not token:
        return Response(
            {
                "error": "NCM access token is not configured in Logistics (api_key required)."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    logistics_from_branch = None
    if logistic_obj:
        logistics_from_branch = getattr(logistic_obj, "branch", None) or getattr(
            logistic_obj, "client_secret", None
        )

    fbranch_val = validated_data.get("fbranch") or logistics_from_branch or ""
    fbranch = str(fbranch_val).strip() if fbranch_val else ""

    destination_branch = (
        validated_data.get("branch")
        or validated_data.get("location_name")
        or validated_data.get("location")
        or ""
    )
    branch = str(destination_branch).strip() if destination_branch else ""

    vref_id = str(validated_data.get("vref_id", "")).strip()
    matching_order = None
    if vref_id:
        matching_order = Order.objects.filter(order_number=vref_id).first()
        if not matching_order and vref_id.isdigit():
            matching_order = Order.objects.filter(id=int(vref_id)).first()

    is_order_paid = str(validated_data.get("is_paid", "")).lower() in [
        "true",
        "1",
        "yes",
    ] or (matching_order and getattr(matching_order, "is_paid", False) is True)

    if is_order_paid:
        cod_charge = "0"
    else:
        raw_cod = validated_data.get("cod_charge")
        cod_charge = str(raw_cod).strip() if raw_cod is not None else ""
        if not cod_charge and matching_order:
            if matching_order.payment_type == "split":
                cash_amount = getattr(matching_order, "cash_amount", 0) or 0
                cod_charge = (
                    str(int(cash_amount))
                    if float(cash_amount).is_integer()
                    else str(cash_amount)
                )
            elif matching_order.payment_type in [
                "cod",
                "cash_on_delivery",
                "cash",
                None,
            ]:
                total = getattr(matching_order, "total_amount", 0) or 0
                cod_charge = (
                    str(int(total)) if float(total).is_integer() else str(total)
                )
            else:
                cod_charge = "0"

    payload = {
        "name": str(validated_data.get("name", "")).strip(),
        "phone": clean_phone_number(validated_data.get("phone")),
        "phone2": clean_phone_number(validated_data.get("phone2", "")),
        "cod_charge": str(cod_charge),
        "address": str(validated_data.get("address", "")).strip(),
        "fbranch": fbranch,
        "branch": branch,
        "package": str(validated_data.get("package", "")).strip(),
        "vref_id": vref_id,
        "instruction": str(validated_data.get("instruction", "")).strip(),
        "delivery_type": str(validated_data.get("delivery_type", "Door2Door")).strip(),
        "weight": str(validated_data.get("weight", "1")).strip(),
    }

    # Validate required fields
    validation_errors = {}
    if not payload["name"]:
        validation_errors["name"] = "Invalid Name"
    if not payload["phone"]:
        validation_errors["phone"] = "Invalid Phone Number"
    if payload["cod_charge"] is None or str(payload["cod_charge"]).strip() == "":
        validation_errors["cod_charge"] = "Invalid COD Amount"
    if not payload["address"]:
        validation_errors["address"] = "Invalid Address"
    if not payload["fbranch"]:
        validation_errors["fbranch"] = (
            "From branch (fbranch) is required. Set branch or client_secret in Logistics, or provide fbranch in request."
        )
    if not payload["branch"]:
        validation_errors["branch"] = "Invalid Branch"

    if validation_errors:
        return Response(
            {"Error": validation_errors}, status=status.HTTP_400_BAD_REQUEST
        )

    status_code, response_data = call_ncm_order_api(payload, token, ncm_base_url)

    # If vref_id matches an order in the database, link the orderid
    vref_id = payload.get("vref_id")
    if status_code == 200 and "orderid" in response_data and vref_id:
        matching_order = Order.objects.filter(order_number=vref_id).first()
        if matching_order:
            old_status = matching_order.status
            matching_order.status = "shipped"
            update_fields = ["status"]
            if hasattr(matching_order, "ncm_order_id"):
                matching_order.ncm_order_id = str(response_data.get("orderid"))
                update_fields.append("ncm_order_id")
            try:
                matching_order.save(update_fields=update_fields)
            except Exception:
                matching_order.save(update_fields=["status"])
            if old_status == "pending":
                matching_order.deduct_stock()

    return Response(
        response_data,
        status=status_code
        if status_code in [200, 400, 401, 403, 404, 422, 500, 502]
        else status.HTTP_200_OK,
    )


def map_ncm_status(
    event: Optional[str] = None, status_str: Optional[str] = None
) -> Optional[str]:
    """
    Maps NCM webhook event / status strings to internal Order.status choices:
    'pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled'.
    """
    event_clean = str(event or "").strip().lower().replace(" ", "_").replace("-", "_")
    status_clean = (
        str(status_str or "").strip().lower().replace("_", " ").replace("-", " ")
    )

    status_map = {
        # Events defined in NCM documentation
        "pickup_completed": "shipped",
        "order_dispatched": "shipped",
        "order_arrived": "shipped",
        "sent_for_delivery": "shipped",
        "delivery_completed": "delivered",
        # Status names defined in NCM documentation
        "pickup complete": "shipped",
        "dispatched": "shipped",
        "arrived": "shipped",
        "sent for delivery": "shipped",
        "in transit": "shipped",
        "delivered": "delivered",
        # Cancellation / Return / Failure variations
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "returned": "cancelled",
        "failed": "cancelled",
        "delivery_failed": "cancelled",
        "order_cancelled": "cancelled",
        "order_returned": "cancelled",
        "return_completed": "cancelled",
        "rto": "cancelled",
        "undelivered": "cancelled",
    }

    if event_clean in status_map:
        return status_map[event_clean]
    if status_clean in status_map:
        return status_map[status_clean]

    # Substring matching fallbacks
    if "deliver" in status_clean or "deliver" in event_clean:
        if "fail" in status_clean or "fail" in event_clean or "un" in status_clean:
            return "cancelled"
        return "delivered"
    if "dispatch" in status_clean or "dispatch" in event_clean:
        return "shipped"
    if "transit" in status_clean or "sent" in status_clean:
        return "shipped"
    if "arrive" in status_clean or "arrive" in event_clean:
        return "shipped"
    if "pickup" in status_clean or "pickup" in event_clean:
        return "shipped"
    if (
        "cancel" in status_clean
        or "return" in status_clean
        or "fail" in status_clean
        or "rto" in status_clean
    ):
        return "cancelled"

    return None


def _apply_order_status_update(order: Order, new_status: str) -> Tuple[str, str]:
    """
    Safely transitions order status, updates payment if delivered, and manages inventory stock.
    Prevents out-of-order backwards transitions (e.g. delivered -> shipped).
    """
    old_status = order.status

    # 1. Prevent out-of-order transition: Once delivered, do not revert to earlier statuses
    if old_status == "delivered" and new_status in [
        "processing",
        "shipped",
        "confirmed",
        "pending",
    ]:
        logger.info(
            f"Order #{order.id} ({order.order_number}) is already delivered. Ignoring backwards transition to '{new_status}'."
        )
        return old_status, old_status

    # 2. Once shipped, do not revert to processing or pending
    if old_status == "shipped" and new_status in ["processing", "confirmed", "pending"]:
        logger.info(
            f"Order #{order.id} ({order.order_number}) is already shipped. Ignoring backwards transition to '{new_status}'."
        )
        return old_status, old_status

    if old_status == new_status:
        if new_status == "delivered" and not order.is_paid:
            order.is_paid = True
            order.save(update_fields=["is_paid"])
        return old_status, new_status

    order.status = new_status
    update_fields = ["status"]

    if new_status == "delivered":
        order.is_paid = True
        update_fields.append("is_paid")

    order.save(update_fields=update_fields)

    # Manage inventory stock transitions
    if old_status == "pending" and new_status in [
        "confirmed",
        "processing",
        "shipped",
        "delivered",
    ]:
        order.deduct_stock()
    elif old_status not in ["pending", "cancelled"] and new_status in [
        "pending",
        "cancelled",
    ]:
        order.return_stock()

    logger.info(
        f"Order #{order.id} ({order.order_number}) updated from {old_status} to {new_status} via NCM webhook."
    )
    return old_status, new_status


def process_ncm_webhook(
    data: Dict[str, Any],
    schema_name: Optional[str] = None,
    request_tenant: Any = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Processes incoming NCM webhook requests for both single and bulk order updates,
    supporting multi-tenant schema isolation.
    """
    target_schema_desc = (
        schema_name
        or getattr(request_tenant, "schema_name", None)
        or "Auto-Detect Across Schemas"
    )

    print("================== NCM WEBHOOK RECEIVED ==================")
    print(f"Target Schema: {target_schema_desc}")
    try:
        print(f"Payload:\n{json.dumps(data, indent=4, ensure_ascii=False)}")
    except Exception:
        print(f"Payload: {data}")
    print("==========================================================")

    # 1. Handle Test Webhook
    is_test = (
        data.get("test") is True
        or str(data.get("test", "")).lower() in ["true", "1", "yes"]
        or str(data.get("order_id", "")).startswith("TEST-")
        or str(data.get("event", "")).lower() == "order.status.changed"
    )
    if is_test:
        logger.info(f"NCM test webhook received for schema: {schema_name}")
        return 200, {
            "status": "success",
            "message": "Test webhook received successfully",
            "schema": schema_name,
        }

    # 2. Extract Order IDs (supports single order_id and bulk order_ids)
    raw_order_ids = data.get("order_ids") or []
    if not isinstance(raw_order_ids, list):
        raw_order_ids = [raw_order_ids]

    single_id = data.get("order_id") or data.get("orderid") or data.get("orderId")
    if single_id and single_id not in raw_order_ids:
        raw_order_ids.append(single_id)

    order_ids = [str(oid).strip() for oid in raw_order_ids if str(oid).strip()]

    if not order_ids:
        return 400, {
            "error": "Missing order_id or order_ids in webhook payload",
            "received_payload": data,
        }

    # 3. Map status / event
    raw_status = data.get("status")
    raw_event = data.get("event")
    new_status = map_ncm_status(raw_event, raw_status)

    if not new_status:
        logger.warning(
            f"NCM webhook received unmapped status '{raw_status}' / event '{raw_event}'"
        )
        return 200, {
            "status": "received",
            "message": f"Webhook acknowledged. Status '{raw_status}' (event: '{raw_event}') does not require order status change.",
            "order_ids": order_ids,
        }

    # 4. Resolve Target Tenant Schema
    resolved_schema = schema_name
    if (
        not resolved_schema
        and request_tenant
        and getattr(request_tenant, "schema_name", None) not in ["public", None]
    ):
        resolved_schema = request_tenant.schema_name

    updated_orders: List[Dict[str, Any]] = []
    not_found_ids = list(order_ids)

    def update_orders_in_schema(schema: str):
        with schema_context(schema):
            for oid in list(not_found_ids):
                q_lookup = Q(ncm_order_id=oid) | Q(order_number=oid)
                if oid.isdigit():
                    q_lookup |= Q(id=int(oid))

                matching_orders = Order.objects.filter(q_lookup)
                for order in matching_orders:
                    old_st, new_st = _apply_order_status_update(order, new_status)
                    updated_orders.append({
                        "order_id": order.id,
                        "order_number": order.order_number,
                        "ncm_order_id": order.ncm_order_id or oid,
                        "old_status": old_st,
                        "new_status": new_st,
                        "schema": schema,
                    })
                    if oid in not_found_ids:
                        not_found_ids.remove(oid)

    if resolved_schema:
        client = Client.objects.filter(schema_name__iexact=resolved_schema).first()
        if not client:
            return 404, {"error": f"Tenant schema '{resolved_schema}' not found"}

        update_orders_in_schema(client.schema_name)
    else:
        # Fallback: Auto-detect by searching active tenant schemas
        active_clients = Client.objects.exclude(schema_name="public")
        for client in active_clients:
            if not not_found_ids:
                break
            update_orders_in_schema(client.schema_name)

    return 200, {
        "status": "received",
        "message": f"Successfully processed {len(updated_orders)} order update(s)",
        "updated_orders": updated_orders,
        "unmatched_order_ids": not_found_ids,
        "ncm_status": raw_status,
        "ncm_event": raw_event,
        "mapped_status": new_status,
    }
