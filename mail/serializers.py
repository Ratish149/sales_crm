from rest_framework import serializers


class SendPaymentEmailSerializer(serializers.Serializer):
    """
    Serializer to validate incoming payment/donation details required for sending
    customer and admin payment notification emails.
    """
    transaction_id = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Unique transaction reference ID (e.g. TXN-12345678)"
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True,
        help_text="Total payment / donation amount"
    )
    customer_email = serializers.EmailField(
        required=True,
        help_text="Email address of the customer / donor"
    )
    customer_name = serializers.CharField(
        max_length=255,
        required=False,
        default="Valued Customer",
        help_text="Full name of the customer / donor"
    )
    customer_phone = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        default="",
        help_text="Phone number of the customer / donor"
    )
    remarks = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional remarks or donation notes"
    )
    payment_method = serializers.CharField(
        max_length=100,
        required=False,
        default="Online Payment",
        help_text="Method used for payment (e.g., eSewa, Khalti, Bank Transfer, Fonepay)"
    )
    admin_email = serializers.EmailField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Optional admin recipient email override"
    )
    currency = serializers.CharField(
        max_length=10,
        required=False,
        default="NPR",
        help_text="Currency code or symbol (default: NPR)"
    )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value

    def validate_transaction_id(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Transaction ID cannot be empty.")
        return cleaned
