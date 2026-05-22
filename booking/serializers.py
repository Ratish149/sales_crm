# serializers.py
import os

import resend
from django.db import connection
from django.template.loader import render_to_string
from rest_framework import serializers

from .models import Booking

resend.api_key = os.getenv("RESEND_API_KEY")


class BookingSerializer(serializers.ModelSerializer):
    balance_due = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def get_balance_due(self, obj):
        if obj.total_amount is not None and obj.amount_paid is not None:
            return obj.total_amount - obj.amount_paid
        return None

    def get_duration_days(self, obj):
        if obj.start_date and obj.end_date:
            return (obj.end_date - obj.start_date).days
        return None

    def validate(self, data):
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and end <= start:
            raise serializers.ValidationError({
                "end_date": "end_date must be after start_date."
            })

        total = data.get("total_amount")
        paid = data.get("amount_paid")
        if total is not None and paid is not None and paid > total:
            raise serializers.ValidationError({
                "amount_paid": "amount_paid cannot exceed total_amount."
            })

        return data

    def create(self, validated_data):
        booking = super().create(validated_data)
        self.send_booking_email(booking)
        return booking

    def send_booking_email(self, booking):
        try:
            tenant = getattr(connection, "tenant", None)
            if tenant:
                tenant_name = "".join(
                    word.capitalize() for word in tenant.name.replace("-", " ").split()
                )
            else:
                tenant_name = "Nepdora"

            verified_sender = "nepdora@baliyoventures.com"
            from_email = f"{tenant_name} <{verified_sender}>"

            if booking.customer_email:
                context = {
                    "customer_name": booking.customer_name,
                    "booking_id": booking.id,
                    "booking_name": booking.booking_name,
                    "booking_type": booking.booking_type,
                    "start_date": booking.start_date,
                    "end_date": booking.end_date,
                    "guests": booking.guests,
                    "total_amount": booking.total_amount,
                    "amount_paid": booking.amount_paid,
                    "balance_due": self.get_balance_due(booking),
                    "duration_days": self.get_duration_days(booking),
                    "payment_status": booking.payment_status,
                    "status": booking.status,
                    "tenant_name": tenant_name,
                    "created_at": booking.created_at,
                    "notes": booking.notes,
                }
                html_content = render_to_string(
                    "booking/email/booking_confirmation.html", context
                )
                resend.Emails.send({
                    "from": from_email,
                    "to": booking.customer_email,
                    "subject": f"Booking Confirmation #{booking.id} - {booking.booking_name or 'Nepdora'}",
                    "html": html_content,
                })
                print(
                    f"Booking confirmation email sent successfully to {booking.customer_email}"
                )

            if (
                tenant
                and hasattr(tenant, "owner")
                and tenant.owner
                and tenant.owner.email
            ):
                admin_email = tenant.owner.email
                admin_context = {
                    "customer_name": booking.customer_name,
                    "customer_email": booking.customer_email,
                    "customer_phone": booking.customer_phone,
                    "booking_id": booking.id,
                    "booking_name": booking.booking_name,
                    "booking_type": booking.booking_type,
                    "start_date": booking.start_date,
                    "end_date": booking.end_date,
                    "guests": booking.guests,
                    "total_amount": booking.total_amount,
                    "amount_paid": booking.amount_paid,
                    "balance_due": self.get_balance_due(booking),
                    "duration_days": self.get_duration_days(booking),
                    "payment_status": booking.payment_status,
                    "status": booking.status,
                    "tenant_name": tenant_name,
                    "created_at": booking.created_at,
                    "notes": booking.notes,
                }
                admin_html_content = render_to_string(
                    "booking/email/admin_new_booking.html", admin_context
                )
                resend.Emails.send({
                    "from": from_email,
                    "to": admin_email,
                    "subject": f"New Booking Received #{booking.id} - {booking.customer_name}",
                    "html": admin_html_content,
                })
                print(f"Admin booking notification sent successfully to {admin_email}")

        except Exception as e:
            print(f"Email sending failed for booking {booking.id}: {e}")


class BookingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view."""

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_type",
            "booking_name",
            "customer_name",
            "customer_email",
            "customer_phone",
            "guests",
            "start_date",
            "end_date",
            "total_amount",
            "status",
            "payment_status",
            "created_at",
        ]
