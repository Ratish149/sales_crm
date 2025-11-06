import requests
from django.utils import timezone

from .models import Conversation


def sync_conversations_from_facebook(page):
    """
    Fully sync all conversations for a Facebook page.
    The DB will exactly mirror Facebook's conversations:
    - New conversations are added
    - Updated conversations are updated
    - Deleted conversations are removed
    """
    print(f"🔄 Syncing conversations for {page.page_name}...")

    url = f"https://graph.facebook.com/v20.0/{page.page_id}/conversations"
    params = {
        "access_token": page.page_access_token,
        "fields": "participants,snippet,updated_time",
    }

    fb_ids = set()
    while url:
        response = requests.get(url, params=params)
        data = response.json()

        if "data" not in data:
            break

        for conv in data["data"]:
            conv_id = conv["id"]
            fb_ids.add(conv_id)

            participants = [
                {"id": p.get("id"), "name": p.get("name")}
                for p in conv.get("participants", {}).get("data", [])
            ]

            Conversation.objects.update_or_create(
                conversation_id=conv_id,
                defaults={
                    "page": page,
                    "participants": participants,
                    "snippet": conv.get("snippet", ""),
                    "updated_time": conv.get("updated_time", timezone.now()),
                    "last_synced": timezone.now(),
                },
            )

        url = data.get("paging", {}).get("next", None)
        params = {}

    # Remove conversations that no longer exist on Facebook
    Conversation.objects.filter(page=page).exclude(conversation_id__in=fb_ids).delete()

    print(f"✅ Fully synced {len(fb_ids)} conversations for {page.page_name}")
    return {"total_conversations": len(fb_ids)}


def sync_messages_for_conversation(conversation):
    """
    Fully sync all messages for a conversation.
    The DB messages will exactly match Facebook:
    - New messages are added
    - Updated messages are updated
    - Deleted messages are removed
    """
    print(f"🔄 Syncing messages for conversation {conversation.conversation_id}...")

    page = conversation.page
    url = f"https://graph.facebook.com/v20.0/{conversation.conversation_id}/messages"
    params = {
        "access_token": page.page_access_token,
        "fields": "id,from,message,created_time",
    }

    fb_messages = []
    fb_ids = set()

    while url:
        response = requests.get(url, params=params)
        data = response.json()

        if "data" not in data:
            break

        for msg in data["data"]:
            msg_id = msg.get("id")
            fb_ids.add(msg_id)
            fb_messages.append(
                {
                    "id": msg_id,
                    "from": msg.get("from", {}),
                    "message": msg.get("message", ""),
                    "created_time": msg.get("created_time", ""),
                }
            )

        url = data.get("paging", {}).get("next", None)
        params = {}

    # Sort messages by created_time
    fb_messages.sort(key=lambda x: x.get("created_time", ""))

    # Update conversation
    conversation.messages = fb_messages
    conversation.last_synced = timezone.now()
    if fb_messages:
        conversation.snippet = fb_messages[-1].get("message", "")
    else:
        conversation.snippet = ""
    conversation.save()

    print(
        f"✅ Fully synced {len(fb_messages)} messages for {conversation.conversation_id}"
    )
    return {"total_messages": len(fb_messages)}
