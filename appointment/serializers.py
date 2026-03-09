from rest_framework import serializers

from .models import Appointment, AppointmentReason


class AppointmentReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentReason
        fields = "__all__"


class AppointmentSerializer(serializers.ModelSerializer):
    reason = AppointmentReasonSerializer(read_only=True)
    reason_id = serializers.PrimaryKeyRelatedField(
        queryset=AppointmentReason.objects.all(),
        write_only=True,
        required=False,
        source="reason",
    )

    class Meta:
        model = Appointment
        fields = [
            "id",
            "full_name",
            "phone",
            "email",
            "message",
            "reason_id",
            "reason",
            "date",
            "time",
            "status",
            "created_at",
            "updated_at",
        ]
