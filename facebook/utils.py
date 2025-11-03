import requests
from django.utils import timezone

from .models import Conversation


def sync_conversations_from_facebook(page):
    """
    Fetch all conversations for a Facebook page and save/update in DB.
    Also extracts participants' names.
    """
    url = f"https://graph.facebook.com/v20.0/{page.page_id}/conversations"
    params = {
        "access_token": page.page_access_token,
        "fields": "participants,snippet,updated_time",
    }

    total_count = 0
    while url:
        response = requests.get(url, params=params)
        data = response.json()

        if "data" not in data:
            break

        for conv in data["data"]:
            participants = [
                {"id": p.get("id"), "name": p.get("name")}
                for p in conv.get("participants", {}).get("data", [])
            ]

            Conversation.objects.update_or_create(
                conversation_id=conv["id"],
                defaults={
                    "page": page,
                    "participants": participants,
                    "snippet": conv.get("snippet", ""),
                    "updated_time": conv.get("updated_time", timezone.now()),
                },
            )
            total_count += 1

        url = data.get("paging", {}).get("next", None)
        params = {}

    return total_count


def sync_messages_for_conversation(conversation, force_refresh=False):
    """
    Fetch all messages for a given conversation.
    Stores messages along with sender name, message text, and created_time.
    Updates snippet to latest message.
    """
    if not force_refresh and conversation.last_synced:
        elapsed = (timezone.now() - conversation.last_synced).total_seconds()
        if elapsed < 0:
            return {"skipped": True}

    page = conversation.page
    url = f"https://graph.facebook.com/v20.0/{conversation.conversation_id}/messages"
    params = {
        "access_token": page.page_access_token,
        "fields": "from,message,created_time",
    }

    all_messages = []
    seen_ids = {m.get("id") for m in (conversation.messages or [])}

    while url:
        response = requests.get(url, params=params)
        data = response.json()

        if "data" not in data:
            break

        for message in data["data"]:
            if message.get("id") not in seen_ids:
                all_messages.append(
                    {
                        "id": message.get("id"),
                        "from": message.get("from", {}),
                        "message": message.get("message", ""),
                        "created_time": message.get("created_time", ""),
                    }
                )
                seen_ids.add(message.get("id"))

        url = data.get("paging", {}).get("next", None)
        params = {}

    # Merge new messages with existing
    existing = conversation.messages or []
    merged = existing + all_messages
    merged.sort(key=lambda x: x.get("created_time", ""))

    conversation.messages = merged
    conversation.last_synced = timezone.now()

    # Update snippet with latest message
    if merged:
        conversation.snippet = merged[-1].get("message", "")

    conversation.save()

    return {"new_messages": len(all_messages), "total": len(merged)}
