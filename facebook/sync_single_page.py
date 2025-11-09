import requests
from dateutil.parser import parse as parse_datetime
from django.utils import timezone
from tqdm import tqdm  # ✅ for progress bars

from .models import Conversation, Facebook


# -------------------------------------------------
# Profile picture cache
# -------------------------------------------------
class ProfilePictureCache:
    def __init__(self):
        self.user_cache = {}
        self.page_cache = {}

    def get_user(self, user_id):
        return self.user_cache.get(user_id)

    def set_user(self, user_id, url):
        self.user_cache[user_id] = url

    def get_page(self, page_id):
        return self.page_cache.get(page_id)

    def set_page(self, page_id, url):
        self.page_cache[page_id] = url


profile_cache = ProfilePictureCache()


def fetch_profile_picture(user_id, access_token, current_url=None, is_page=False):
    """
    Fetch and cache profile picture for a Facebook user or page.
    """
    cache_get = profile_cache.get_page if is_page else profile_cache.get_user
    cache_set = profile_cache.set_page if is_page else profile_cache.set_user

    cached_url = cache_get(user_id)
    if cached_url:
        return cached_url

    if current_url:
        cache_set(user_id, current_url)
        return current_url

    try:
        url = f"https://graph.facebook.com/{user_id}"
        params = {"fields": "picture.type(large)", "access_token": access_token}
        resp = requests.get(url, params=params, timeout=5).json()
        pic_url = resp.get("picture", {}).get("data", {}).get("url")
        if pic_url:
            cache_set(user_id, pic_url)
        return pic_url
    except Exception as e:
        print(f"⚠️ Failed to fetch profile picture for {user_id}: {e}")
        return None


# -------------------------------------------------
# Main sync function
# -------------------------------------------------
def sync_facebook_page(page: Facebook):
    """
    Sync all conversations and messages for the given Facebook page.
    Works per-tenant (called inside the tenant schema context).
    Shows progress bars for better visibility.
    """
    access_token = page.page_access_token
    page_id = page.page_id
    page_profile_pic = fetch_profile_picture(page_id, access_token, is_page=True)

    # ------------------------------
    # Fetch Conversations
    # ------------------------------
    print(f"🔄 Syncing conversations for {page.page_name} ({page_id})")
    url = f"https://graph.facebook.com/v20.0/{page_id}/conversations"
    params = {
        "access_token": access_token,
        "fields": "participants,snippet,updated_time",
    }

    fb_ids = set()
    all_conversations = []

    # First gather all conversations
    while url:
        response = requests.get(url, params=params)
        data = response.json()

        if "data" not in data:
            print(f"⚠️ No data found for page {page.page_name}")
            break

        all_conversations.extend(data["data"])
        url = data.get("paging", {}).get("next")
        params = {}

    # Process conversations with a progress bar
    for conv in tqdm(all_conversations, desc="📩 Syncing Conversations", unit="conv"):
        conv_id = conv["id"]
        fb_ids.add(conv_id)

        # Build participants
        participants = []
        for p in conv.get("participants", {}).get("data", []):
            participants.append(
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "profile_pic": page_profile_pic if p.get("id") == page_id else None,
                    "is_page": p.get("id") == page_id,
                }
            )

        # Update participants’ profile pics
        updated = False
        for p in participants:
            if p.get("is_page"):
                continue
            current_pic = p.get("profile_pic")
            new_pic = fetch_profile_picture(
                p["id"], access_token, current_url=current_pic
            )
            if new_pic and new_pic != current_pic:
                p["profile_pic"] = new_pic
                updated = True

        updated_time = conv.get("updated_time")
        updated_time = parse_datetime(updated_time) if updated_time else timezone.now()

        convo_obj, created = Conversation.objects.get_or_create(
            conversation_id=conv_id,
            defaults={
                "page": page,
                "participants": participants,
                "snippet": conv.get("snippet", ""),
                "updated_time": updated_time,
                "last_synced": timezone.now(),
            },
        )

        if not created and updated:
            convo_obj.participants = participants
            convo_obj.save(update_fields=["participants"])

    # Remove deleted conversations
    Conversation.objects.filter(page=page).exclude(conversation_id__in=fb_ids).delete()

    # ------------------------------
    # Fetch Messages for each conversation
    # ------------------------------
    conversations = Conversation.objects.filter(page=page)
    print(f"💬 Syncing messages for {len(conversations)} conversations...")

    for conversation in tqdm(
        conversations, desc="💭 All Conversations Progress", unit="conv"
    ):
        url = (
            f"https://graph.facebook.com/v20.0/{conversation.conversation_id}/messages"
        )
        params = {
            "access_token": access_token,
            "fields": "id,from,message,created_time,attachments,sticker",
        }

        fb_messages = []
        fb_ids = set()
        participants_map = {p["id"]: p for p in (conversation.participants or [])}

        # Ensure page has profile pic
        if page_id in participants_map:
            participants_map[page_id]["profile_pic"] = page_profile_pic

        all_messages = []
        while url:
            response = requests.get(url, params=params)
            data = response.json()
            if "data" not in data:
                break

            all_messages.extend(data["data"])
            url = data.get("paging", {}).get("next")
            params = {}

        # Message progress bar for this conversation
        for msg in tqdm(
            all_messages,
            desc=f"📨 {conversation.conversation_id}",
            leave=False,
            unit="msg",
        ):
            msg_id = msg.get("id")
            fb_ids.add(msg_id)

            created_time = msg.get("created_time")
            created_time = (
                parse_datetime(created_time).isoformat()
                if created_time
                else timezone.now().isoformat()
            )

            # Handle attachments
            attachments = []
            for att in msg.get("attachments", {}).get("data", []):
                att_type = att.get("type") or att.get("mime_type")
                att_url = (
                    att.get("file_url")
                    or att.get("url")
                    or att.get("image_data", {}).get("url")
                    or att.get("payload", {}).get("url")
                )
                sticker_id = att.get("payload", {}).get("sticker_id") or att.get(
                    "image_data", {}
                ).get("sticker_id")
                attachments.append(
                    {"type": att_type, "url": att_url, "sticker_id": sticker_id}
                )

            # Handle sticker
            sticker_url = msg.get("sticker")
            if sticker_url:
                attachments.append(
                    {
                        "type": "sticker",
                        "url": sticker_url,
                        "sticker_id": sticker_url.split("/")[-1].split("_")[0],
                    }
                )

            sender = msg.get("from", {})
            sender_id = sender.get("id")

            # Add sender’s profile picture
            if sender_id == page_id:
                sender["profile_pic"] = page_profile_pic
            elif sender_id:
                current_pic = participants_map.get(sender_id, {}).get("profile_pic")
                sender_pic = fetch_profile_picture(
                    sender_id, access_token, current_url=current_pic
                )
                if sender_pic:
                    sender["profile_pic"] = sender_pic
                    participants_map[sender_id] = {
                        "id": sender_id,
                        "name": sender.get("name", ""),
                        "profile_pic": sender_pic,
                        "is_page": False,
                    }

            fb_messages.append(
                {
                    "id": msg_id,
                    "from": sender,
                    "message": msg.get("message", ""),
                    "created_time": created_time,
                    "attachments": attachments,
                }
            )

        fb_messages.sort(key=lambda x: x.get("created_time", ""))
        conversation.messages = fb_messages
        conversation.last_synced = timezone.now()
        conversation.snippet = fb_messages[-1].get("message", "") if fb_messages else ""
        conversation.participants = list(participants_map.values())
        conversation.save()

    print(f"✅ Sync completed for page {page.page_name}")
    return {"status": "success", "total_conversations": conversations.count()}
