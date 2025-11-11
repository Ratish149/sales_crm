import json
import requests
from celery import shared_task
from django_tenants.utils import schema_context
from .models import Facebook
from .sync_single_page import sync_facebook_page


@shared_task
def sync_page_task(page_id: str, tenant_schema: str, frontend_url: str, limit=30, after=None):
    """
    Celery task to sync a Facebook page and notify frontend when done.
    """
    with schema_context(tenant_schema):
        page = Facebook.objects.get(page_id=page_id)
        result = sync_facebook_page(page, limit=limit, after=after)

    # Notify frontend
    try:
        frontend_url = f"{frontend_url}/api/notify-sync/"
        payload = {
            "tenant": tenant_schema,
            "type": "sync_page_complete",
            "data": {
                "page_id": page_id,
                "total_conversations": result["total_conversations"],
                "has_next": result["has_next"],
                "next_after": result["next_after"]
            }
        }
        print("Payload to frontend:", json.dumps(payload, indent=2))
        response = requests.post(frontend_url, json=payload, timeout=5)
        if response.status_code == 200:
            print("Frontend notified successfully.")
            print(response.json())
        else:
            print(f"⚠️ Failed to notify frontend: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Failed to notify frontend: {e}")
