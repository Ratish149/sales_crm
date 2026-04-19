import requests
from django.conf import settings
from django.db import transaction
from django_tenants.utils import tenant_context

from nepdora_payment.models import SMSPurchaseHistory

from .models import SMSSendHistory, SMSSetting


def calculate_sms_credits(message):
    """
    Calculates the number of credits used based on message length.
    - < 160 characters: 1 credit
    - <= 315 characters: 2 credits
    - > 315 characters: 3 credits
    """
    length = len(message)
    if length < 160:
        return 1
    if length <= 315:
        return 2
    return 3


def send_sms(to, text):
    """
    Sends an SMS using Aakash SMS and tracks credits.
    :param to: Receiver number (10 digits)
    :param text: Message text
    """
    cost = calculate_sms_credits(text)
    setting = SMSSetting.load()

    if setting.sms_credit < cost:
        return {
            "success": False,
            "message": f"Insufficient SMS credits. Required: {cost}, Available: {setting.sms_credit}",
        }

    auth_token = getattr(settings, "AAKASH_SMS_TOKEN", None)
    if not auth_token:
        return {
            "success": False,
            "message": "AAKASH_SMS_TOKEN not configured in settings.",
        }

    try:
        r = requests.post(
            "https://sms.aakashsms.com/sms/v3/send/",
            data={"auth_token": auth_token, "to": to, "text": text},
        )

        status_code = r.status_code
        try:
            response_json = r.json()
        except ValueError:
            response_json = {"raw_text": r.text}

        with transaction.atomic():
            # Deduct credit
            setting.sms_credit -= cost
            setting.save()

            # Log history
            SMSSendHistory.objects.create(
                receiver_number=to,
                message=text,
                credits_used=cost,
                status=str(status_code),
                response_data=response_json,
            )

        return {
            "success": True,
            "response": response_json,
            "credits_used": cost,
            "remaining_credits": setting.sms_credit,
        }

    except Exception as e:
        return {"success": False, "message": str(e)}


def send_sms_test(to, text):
    """
    Test version of send_sms that prints instead of calling the API.
    Validates credits and deducts them if successful.
    """
    cost = calculate_sms_credits(text)
    setting = SMSSetting.load()

    if setting.sms_credit < cost:
        return {
            "success": False,
            "message": f"Insufficient SMS credits. Required: {cost}, Available: {setting.sms_credit}",
        }

    print("------- SMS TEST START -------")
    print(f"To: {to}")
    print(f"Message: {text}")
    print(f"Credits Required: {cost}")
    print("------- SMS TEST END -------")

    response_json = {
        "success": True,
        "message": "Test SMS successful (Logic only).",
        "test": True,
        "data": {"to": to, "text": text, "cost": cost},
    }

    try:
        with transaction.atomic():
            # Deduct credit
            setting.sms_credit -= cost
            setting.save()

            # Log history
            SMSSendHistory.objects.create(
                receiver_number=to,
                message=text,
                credits_used=cost,
                status="TEST_SUCCESS",
                response_data=response_json,
            )

        return {
            "success": True,
            "response": response_json,
            "credits_used": cost,
            "remaining_credits": setting.sms_credit,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def add_sms_credits(tenant, amount, transaction_id, price=None):
    """
    Adds credits to a client and logs the purchase history.
    """
    with transaction.atomic():
        with tenant_context(tenant):
            setting = SMSSetting.load()
            setting.sms_credit += amount
            setting.save()
            new_balance = setting.sms_credit

        purchase = SMSPurchaseHistory.objects.create(
            tenant=tenant, amount=amount, price=price, transaction_id=transaction_id
        )
    return {
        "success": True,
        "new_balance": new_balance,
        "purchase_id": purchase.id,
    }
