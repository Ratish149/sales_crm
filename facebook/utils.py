from datetime import timedelta

import requests
from django.utils import timezone

from .models import Conversation


def sync_conversations_from_facebook(page, force_refresh=False):
    """
    Fetch all conversations for a Facebook page and save/update in DB.
    Calls the Facebook API only if last sync > 6 hours ago.
    """
    # Check last sync time from any conversation of this page
    last_sync = (
        Conversation.objects.filter(page=page)
        .order_by("-last_synced")
        .values_list("last_synced", flat=True)
        .first()
    )

    # Skip API call if synced within 6 hours and not forced
    if last_sync and not force_refresh:
        elapsed = timezone.now() - last_sync
        if elapsed < timedelta(hours=6):
            print(
                f"⏩ Skipping Facebook API call for {page.page_name}, "
                f"last synced {elapsed} ago."
            )
            return {"skipped": True, "elapsed": str(elapsed)}

    print(f"🔄 Syncing conversations for {page.page_name}...")

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
                    "last_synced": timezone.now(),
                },
            )
            total_count += 1

        url = data.get("paging", {}).get("next", None)
        params = {}  # clear for next request

    print(f"✅ Synced {total_count} conversations for {page.page_name}")
    return {"new_conversations": total_count}


def sync_messages_for_conversation(conversation, force_refresh=False):
    """
    Fetch all messages for a given conversation.
    Calls the Facebook API only if last sync > 6 hours ago.
    """
    # Skip if synced within 6 hours
    if conversation.last_synced and not force_refresh:
        elapsed = timezone.now() - conversation.last_synced
        if elapsed < timedelta(hours=6):
            print(
                f"⏩ Skipping Facebook message sync for {conversation.conversation_id}, "
                f"last synced {elapsed} ago."
            )
            return {"skipped": True, "elapsed": str(elapsed)}

    print(f"🔄 Syncing messages for conversation {conversation.conversation_id}...")

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

    # Merge and update
    existing = conversation.messages or []
    merged = existing + all_messages
    merged.sort(key=lambda x: x.get("created_time", ""))

    conversation.messages = merged
    conversation.last_synced = timezone.now()

    if merged:
        conversation.snippet = merged[-1].get("message", "")

    conversation.save()

    print(
        f"✅ Synced {len(all_messages)} new messages "
        f"({len(merged)} total) for {conversation.conversation_id}"
    )
    return {"new_messages": len(all_messages), "total": len(merged)}
