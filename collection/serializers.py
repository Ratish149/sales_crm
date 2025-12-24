from datetime import datetime

from django.core.validators import EmailValidator
from rest_framework import serializers

from .models import Collection, CollectionData


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for Collection with field validation"""

    all_fields = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = [
            "id",
            "name",
            "slug",
            "default_fields",
            "fields",
            "all_fields",
            "created_at",
            "updated_at",
            "send_email",
            "admin_email",
        ]
        read_only_fields = [
            "id",
            "slug",
            "default_fields",
            "all_fields",
            "created_at",
            "updated_at",
        ]

    def get_all_fields(self, obj):
        """Return combined default and custom fields"""
        return obj.get_all_fields()

    def validate_fields(self, value):
        """Validate the custom fields JSON structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Fields must be a list")

        field_names = []
        valid_types = [
            "text",
            "number",
            "date",
            "boolean",
            "email",
            "image",
            "json",
            "rich_text",
            "model",
        ]

        # Reserved field names (default fields)
        reserved_names = ["name", "content", "slug"]

        for field in value:
            # Check required keys
            if "name" not in field or "type" not in field:
                raise serializers.ValidationError(
                    "Each field must have 'name' and 'type'"
                )

            # Check for reserved field names
            if field["name"] in reserved_names:
                raise serializers.ValidationError(
                    f"Field name '{field['name']}' is reserved. Please use a different name."
                )

            # Check field type
            if field["type"] not in valid_types:
                raise serializers.ValidationError(
                    f"Invalid field type '{field['type']}'. "
                    f"Valid types: {', '.join(valid_types)}"
                )

            # Check for duplicate field names
            if field["name"] in field_names:
                raise serializers.ValidationError(
                    f"Duplicate field name: {field['name']}"
                )
            field_names.append(field["name"])

            # Set default for 'required' if not provided
            if "required" not in field:
                field["required"] = False

            # Set default for 'filterable' if not provided
            if "filterable" not in field:
                field["filterable"] = False

            # Set default for 'searchable' if not provided
            if "searchable" not in field:
                field["searchable"] = False

            # Set default for 'model' if not provided
            if "model" not in field:
                field["model"] = None

            # Check if referenced model exists
            model_ref = field.get("model")
            if model_ref:
                if not Collection.objects.filter(id=model_ref).exists():
                    raise serializers.ValidationError(
                        f"Referenced collection with ID '{model_ref}' does not exist."
                    )

        return value


class CollectionDataSerializer(serializers.ModelSerializer):
    """Serializer for CollectionData with dynamic validation based on collection fields"""

    class Meta:
        model = CollectionData
        fields = ["id", "collection", "data", "created_at", "updated_at"]
        read_only_fields = ["id", "collection", "created_at", "updated_at"]

    def validate(self, attrs):
        """Validate data against the collection's field definitions (default + custom)"""
        collection = attrs.get("collection") or self.context.get("collection")

        if not collection and self.instance:
            collection = self.instance.collection

        if not collection:
            raise serializers.ValidationError(
                "Collection not found in context or attributes"
            )

        data = attrs.get("data", {})

        if not isinstance(data, dict):
            raise serializers.ValidationError({"data": "Data must be a JSON object"})

        # Get all field definitions (default + custom)
        field_definitions = collection.get_all_fields()
        errors = {}

        # Validate each field
        for field_def in field_definitions:
            field_name = field_def["name"]
            field_type = field_def["type"]
            is_required = field_def.get("required", False)
            field_value = data.get(field_name)

            # Check required fields
            if is_required and (field_value is None or field_value == ""):
                errors[field_name] = "This field is required"
                continue

            # Skip validation if field is not provided and not required
            if field_value is None or field_value == "":
                continue

            # Validate based on field type
            try:
                if field_type == "text":
                    if not isinstance(field_value, str):
                        errors[field_name] = "Must be a text value"

                elif field_type == "number":
                    if not isinstance(field_value, (int, float)):
                        try:
                            float(field_value)
                        except (ValueError, TypeError):
                            errors[field_name] = "Must be a number"

                elif field_type == "boolean":
                    if not isinstance(field_value, bool):
                        errors[field_name] = "Must be true or false"

                elif field_type == "date":
                    if isinstance(field_value, str):
                        try:
                            datetime.strptime(field_value, "%Y-%m-%d")
                        except ValueError:
                            errors[field_name] = "Must be a valid date (YYYY-MM-DD)"
                    else:
                        errors[field_name] = "Must be a date string (YYYY-MM-DD)"

                elif field_type == "email":
                    if isinstance(field_value, str):
                        validator = EmailValidator()
                        try:
                            validator(field_value)
                        except serializers.ValidationError:
                            errors[field_name] = "Must be a valid email address"
                    else:
                        errors[field_name] = "Must be an email string"

            except Exception as e:
                errors[field_name] = str(e)

        if errors:
            raise serializers.ValidationError({"data": errors})

        return attrs
