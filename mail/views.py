from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SendPaymentEmailSerializer
from .services.payment_email_service import send_payment_success_emails


class SendPaymentEmailAPIView(APIView):
    """
    API endpoint to send payment completion email notifications.
    Sends HTML email receipt to the customer and notification to the admin/tenant owner.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = SendPaymentEmailSerializer

    @extend_schema(
        request=SendPaymentEmailSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "success"},
                    "message": {"type": "string", "example": "Payment emails sent successfully."},
                    "details": {
                        "type": "object",
                        "properties": {
                            "customer_email_sent": {"type": "boolean"},
                            "admin_email_sent": {"type": "boolean"},
                        },
                    },
                },
            },
            400: {"type": "object"},
        },
        summary="Send custom payment notification email to customer and admin",
    )
    def post(self, request, *args, **kwargs):
        serializer = SendPaymentEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        results = send_payment_success_emails(serializer.validated_data)

        if results.get("customer_email_sent") or results.get("admin_email_sent"):
            return Response(
                {
                    "status": "success",
                    "message": "Payment email notifications processed.",
                    "details": results,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "status": "error",
                    "message": "Failed to send payment email notifications.",
                    "details": results,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
