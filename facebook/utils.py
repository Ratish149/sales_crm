import requests
from dateutil.parser import parse as parse_datetime
from django.utils import timezone
from tqdm import tqdm

from .models import Conversation


# -------------------------------------------------
# Profile picture caches
# -------------------------------------------------
class ProfilePictureCache:
    def __init__(self):
        self.user_cache = {}  # key: user_id, value: url
        self.page_cache = {}  # key: page_id, value: url

    def get_user(self, user_id):
        return self.user_cache.get(user_id)

    def set_user(self, user_id, url):
        self.user_cache[user_id] = url

    def get_page(self, page_id):
        return self.page_cache.get(page_id)

    def set_page(self, page_id, url):
        self.page_cache[page_id] = url


profile_cache = ProfilePictureCache()


# -------------------------------------------------
# Fetch profile picture
# -------------------------------------------------
def fetch_facebook_profile_picture(
    user_id, access_token, current_url=None, is_page=False
):
    cache_get = profile_cache.get_page if is_page else profile_cache.get_user
    cache_set = profile_cache.set_page if is_page else profile_cache.set_user

    # Return cached URL if exists
    cached_url = cache_get(user_id)
    if cached_url:
        return cached_url

    # If current URL exists, reuse it and cache
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
# Update user participants only
# -------------------------------------------------
def update_participants_profile_pics(participants, access_token):
    updated = False
    for p in participants:
        user_id = p.get("id")
        if not user_id or p.get("is_page"):
            continue

        current_pic = p.get("profile_pic")
        new_pic = fetch_facebook_profile_picture(
            user_id, access_token, current_url=current_pic
        )
        if new_pic and new_pic != current_pic:
            p["profile_pic"] = new_pic
            updated = True
    return participants, updated


# -------------------------------------------------
# Sync conversations
# -------------------------------------------------
def sync_conversations_from_facebook(page):
    print(f"🔄 Syncing conversations for {page.page_name}...")

    page_profile_pic = fetch_facebook_profile_picture(
        page.page_id, page.page_access_token, is_page=True
    )

    url = f"https://graph.facebook.com/v20.0/{page.page_id}/conversations"
    params = {
        "access_token": page.page_access_token,
        "fields": "participants,snippet,updated_time",
    }
    fb_ids = set()
    all_conversations = []

    # First, fetch all conversations
    while url:
        response = requests.get(url, params=params)
        data = response.json()
        if "data" not in data:
            break

        all_conversations.extend(data["data"])
        url = data.get("paging", {}).get("next")
        params = {}

    # Process conversations with progress bar
    for conv in tqdm(all_conversations, desc="Syncing Conversations", unit="conv"):
        conv_id = conv["id"]
        fb_ids.add(conv_id)

        participants = []
        for p in conv.get("participants", {}).get("data", []):
            participants.append(
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "profile_pic": page_profile_pic
                    if p.get("id") == page.page_id
                    else None,
                    "is_page": p.get("id") == page.page_id,
                }
            )

        participants, pics_updated = update_participants_profile_pics(
            participants, page.page_access_token
        )

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

        if not created and pics_updated:
            convo_obj.participants = participants
            convo_obj.save(update_fields=["participants"])

    Conversation.objects.filter(page=page).exclude(conversation_id__in=fb_ids).delete()
    print(f"✅ Fully synced {len(fb_ids)} conversations for {page.page_name}")
    return {"total_conversations": len(fb_ids)}


# -------------------------------------------------
# Sync messages for a conversation
# -------------------------------------------------
def sync_messages_for_conversation(conversation):
    page = conversation.page
    page_profile_pic = fetch_facebook_profile_picture(
        page.page_id, page.page_access_token, is_page=True
    )

    url = f"https://graph.facebook.com/v20.0/{conversation.conversation_id}/messages"
    params = {
        "access_token": page.page_access_token,
        "fields": "id,from,message,created_time,attachments,sticker",
    }

    all_messages = []
    while url:
        response = requests.get(url, params=params)
        data = response.json()
        if "data" not in data:
            break
        all_messages.extend(data["data"])
        url = data.get("paging", {}).get("next")
        params = {}

    fb_messages = []
    fb_ids = set()
    participants_map = {p["id"]: p for p in conversation.participants}

    if page.page_id in participants_map:
        participants_map[page.page_id]["profile_pic"] = page_profile_pic

    for msg in tqdm(
        all_messages, desc=f"Messages for {conversation.conversation_id}", unit="msg"
    ):
        msg_id = msg.get("id")
        fb_ids.add(msg_id)

        created_time = msg.get("created_time")
        created_time = (
            parse_datetime(created_time).isoformat()
            if created_time
            else timezone.now().isoformat()
        )

        attachments = []
        for att in msg.get("attachments", {}).get("data", []):
            att_type = att.get("type") or att.get("mime_type")
            url = (
                att.get("file_url")
                or att.get("url")
                or att.get("image_data", {}).get("url")
                or att.get("payload", {}).get("url")
            )
            sticker_id = att.get("payload", {}).get("sticker_id") or att.get(
                "image_data", {}
            ).get("sticker_id")
            attachments.append({"type": att_type, "url": url, "sticker_id": sticker_id})

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

        if sender_id == page.page_id:
            sender["profile_pic"] = page_profile_pic
        elif sender_id:
            current_pic = participants_map.get(sender_id, {}).get("profile_pic")
            sender_pic = fetch_facebook_profile_picture(
                sender_id, page.page_access_token, current_url=current_pic
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

    return {"total_messages": len(fb_messages)}


# -------------------------------------------------
# Sync all page data with unified progress bar
# -------------------------------------------------
def sync_all_page_data(page):
    result = sync_conversations_from_facebook(page)
    conversations = Conversation.objects.filter(page=page)
    print(f"🔄 Syncing messages for {len(conversations)} conversations...")

    for conv in tqdm(conversations, desc="All Messages Progress", unit="conv"):
        sync_messages_for_conversation(conv)

    print("✅ All messages synced for page:", page.page_name)
    return result
