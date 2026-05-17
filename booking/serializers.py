# serializers.py
from rest_framework import serializers

from .models import Booking


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
