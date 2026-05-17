from rest_framework import serializers


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class MultipleFileUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False), allow_empty=False
    )


class FileDeleteSerializer(serializers.Serializer):
    urls = serializers.ListField(child=serializers.URLField(), required=False)

    def validate(self, data):
        if not any([data.get("urls")]):
            raise serializers.ValidationError(
                "At least one of 'urls' must be provided."
            )
        return data
