import requests
from django.utils import timezone

from .models import Conversation


def sync_conversations_from_facebook(page):
    """
    Fetch all conversations for a Facebook page and save/update in DB.
    Handles pagination automatically.
    """
    url = f"https://graph.facebook.com/v20.0/{page.page_id}/conversations"
    params = {"access_token": page.page_access_token}

    total_count = 0
    while url:
        response = requests.get(url, params=params)
        data = response.json()

        if "data" not in data:
            print(f"[ERROR] No conversation data for page {page.page_name}: {data}")
            break

        for conv in data["data"]:
            Conversation.objects.update_or_create(
                conversation_id=conv["id"],
                defaults={
                    "page": page,
                    "participants": conv.get("participants", {}),
                    "snippet": conv.get("snippet", ""),
                    "updated_time": conv.get("updated_time", timezone.now()),
                },
            )
            total_count += 1

        url = data.get("paging", {}).get("next", None)
        params = {}

    print(f"[INFO] Synced {total_count} conversations for {page.page_name}")
    return total_count


def sync_messages_for_conversation(conversation, force_refresh=False):
    """
    Fetch all messages for a given conversation.
    - Uses pagination
    - Avoids duplicates
    - Supports `force_refresh` to reload even if recently synced
    """
    # Skip fetch if already recently synced
    if not force_refresh and conversation.last_synced:
        elapsed = (timezone.now() - conversation.last_synced).total_seconds()
        if elapsed < 60:  # skip if synced within last minute
            print(
                f"[INFO] Skipping fetch for {conversation.conversation_id}, synced {elapsed:.0f}s ago"
            )
            return {"skipped": True}

    page = conversation.page
    url = f"https://graph.facebook.com/v20.0/{conversation.conversation_id}/messages"
    params = {"access_token": page.page_access_token}

    all_messages = []
    seen_ids = {m.get("id") for m in (conversation.messages or [])}

    while url:
        response = requests.get(url, params=params)
        data = response.json()

        if "data" not in data:
            print(f"[ERROR] No messages for {conversation.conversation_id}: {data}")
            break

        for message in data["data"]:
            if message.get("id") not in seen_ids:
                all_messages.append(message)
                seen_ids.add(message.get("id"))

        url = data.get("paging", {}).get("next", None)
        params = {}

    existing = conversation.messages or []
    merged = existing + all_messages
    merged.sort(key=lambda x: x.get("created_time", ""))

    conversation.messages = merged
    conversation.last_synced = timezone.now()
    conversation.save()

    print(
        f"[INFO] Synced {len(all_messages)} new messages for {conversation.conversation_id}"
    )
    return {"new_messages": len(all_messages), "total": len(merged)}
