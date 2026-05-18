from rest_framework import serializers

from .models import Event


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "venue_name",
            "address",
            "city",
            "country",
            "thumbnail",
            "thumbnail_alt_description",
            "organizer_name",
            "organizer_email",
            "organizer_phone",
            "organizer_website",
            "meta_title",
            "meta_description",
            "is_featured",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "End date cannot be before start date."
            })

        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        if (
            start_time
            and end_time
            and start_date
            and end_date
            and start_date == end_date
            and end_time <= start_time
        ):
            raise serializers.ValidationError({
                "end_time": "End time must be after start time for single-day events."
            })

        return attrs


class EventListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "start_date",
            "end_date",
            "start_time",
            "city",
            "country",
            "venue_name",
            "thumbnail",
            "is_featured",
            "tags",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "created_at"]
