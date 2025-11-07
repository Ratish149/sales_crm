from rest_framework import serializers

from .models import Conversation, Facebook


class FacebookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facebook
        fields = "__all__"


class ConversationSerializer(serializers.ModelSerializer):
    page_name = serializers.CharField(source="page.page_name", read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "page",
            "page_name",
            "conversation_id",
            "participants",
            "snippet",
            "updated_time",
            # "messages",
            "last_synced",
        ]


class ConversationMessageSerializer(serializers.ModelSerializer):
    page_name = serializers.CharField(source="page.page_name", read_only=True)
    messages = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "page",
            "page_name",
            "conversation_id",
            "participants",
            "snippet",
            "updated_time",
            "messages",
            "last_synced",
        ]

    def get_messages(self, obj):
        request = self.context.get("request")
        limit = int(request.query_params.get("limit", 20)) if request else 20
        offset = int(request.query_params.get("offset", 0)) if request else 0

        # Return newest messages first
        messages = obj.messages[::-1]  # reverse order: newest → oldest
        return messages[offset : offset + limit]
