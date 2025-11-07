import requests
from dateutil.parser import parse as parse_datetime
from django.utils import timezone

from .models import Conversation


def sync_conversations_from_facebook(page):
    """
    Fully sync all conversations for a Facebook page.
    - Adds new conversations
    - Updates existing conversations
    - Removes conversations that no longer exist on FB
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

            updated_time = conv.get("updated_time")
            if updated_time:
                updated_time = parse_datetime(updated_time)
            else:
                updated_time = timezone.now()

            Conversation.objects.update_or_create(
                conversation_id=conv_id,
                defaults={
                    "page": page,
                    "participants": participants,
                    "snippet": conv.get("snippet", ""),
                    "updated_time": updated_time,
                    "last_synced": timezone.now(),
                },
            )

        url = data.get("paging", {}).get("next")
        params = {}

    # Delete conversations that no longer exist on FB
    Conversation.objects.filter(page=page).exclude(conversation_id__in=fb_ids).delete()

    print(f"✅ Fully synced {len(fb_ids)} conversations for {page.page_name}")
    return {"total_conversations": len(fb_ids)}


def sync_messages_for_conversation(conversation):
    """
    Fully sync all messages for a conversation.
    - Adds new messages
    - Updates existing messages
    - Removes deleted messages
    """
    print(f"🔄 Syncing messages for conversation {conversation.conversation_id}...")

    page = conversation.page
    url = f"https://graph.facebook.com/v20.0/{conversation.conversation_id}/messages"
    params = {
        "access_token": page.page_access_token,
        "fields": "id,from,message,created_time,attachments,sticker",
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

            # Parse created_time to datetime
            created_time = msg.get("created_time")
            if created_time:
                created_time = parse_datetime(created_time).isoformat()
            else:
                created_time = timezone.now().isoformat()

            # Process attachments if present
            attachments = []
            for att in msg.get("attachments", {}).get("data", []):
                att_type = att.get("type") or att.get("mime_type")

                # Get URL from the appropriate field depending on attachment type
                url = (
                    att.get("file_url")  # for audio/video
                    or att.get("url")  # sometimes URL is directly here
                    or att.get("image_data", {}).get("url")  # for images
                    or att.get("payload", {}).get("url")  # fallback to payload
                )

                # Get sticker_id from payload or image_data if available
                sticker_id = att.get("payload", {}).get("sticker_id") or att.get(
                    "image_data", {}
                ).get("sticker_id")

                attachments.append(
                    {
                        "type": att_type,
                        "url": url,
                        "sticker_id": sticker_id,
                    }
                )
            sticker_url = msg.get("sticker")
            if sticker_url:
                attachments.append(
                    {
                        "type": "sticker",
                        "url": sticker_url,
                        "sticker_id": sticker_url.split("/")[-1].split("_")[
                            0
                        ],  # optional: extract ID from URL
                    }
                )

            fb_messages.append(
                {
                    "id": msg_id,
                    "from": msg.get("from", {}),
                    "message": msg.get("message", ""),
                    "created_time": created_time,
                    "attachments": attachments,
                }
            )

        url = data.get("paging", {}).get("next")
        params = {}

    # Sort messages by created_time
    fb_messages.sort(key=lambda x: x.get("created_time", ""))

    # Update conversation
    conversation.messages = fb_messages
    conversation.last_synced = timezone.now()
    conversation.snippet = fb_messages[-1].get("message", "") if fb_messages else ""
    conversation.save()

    print(
        f"✅ Fully synced {len(fb_messages)} messages for {conversation.conversation_id}"
    )
    return {"total_messages": len(fb_messages)}


def sync_all_page_data(page):
    """
    Helper function to sync conversations and messages for a page.
    """
    result = sync_conversations_from_facebook(page)
    conversations = Conversation.objects.filter(page=page)
    for conv in conversations:
        sync_messages_for_conversation(conv)
    return result
