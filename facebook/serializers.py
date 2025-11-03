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
