import logging
from datetime import timedelta

from celery import shared_task
from django.db import connection, transaction
from django.utils import timezone

from tenants.models import Client

from .models import CustomUser

logger = logging.getLogger(__name__)


@shared_task
def auto_purge_deleted_users():
    """
    Finds users soft-deleted more than 7 days ago and permanently deletes them.
    Also drops their associated tenant schemas.
    """
    # Use timezone.now() to get current time with timezone awareness
    expiry_threshold = timezone.now() - timedelta(days=7)

    # We use all_objects or manually filter for is_deleted=True
    # Since we removed the custom manager, CustomUser.objects.all() includes deleted users.
    # However, we should be explicit.
    expired_users = CustomUser.objects.filter(
        is_deleted=True, deleted_at__lte=expiry_threshold
    )

    count = expired_users.count()
    if count == 0:
        logger.info("No expired soft-deleted users to purge.")
        return "No expired users found."

    purged_count = 0
    for user in expired_users:
        try:
            tenant = Client.objects.filter(owner=user).first()
            schema_name = tenant.schema_name if tenant else None

            with transaction.atomic():
                if schema_name:
                    # Drop the tenant schema
                    with connection.cursor() as cursor:
                        cursor.execute(
                            f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;'
                        )
                    logger.info(f"Dropped schema {schema_name} for user {user.email}")

                # Permanently delete the user record from the database
                user_email = user.email
                user.delete()
                purged_count += 1
                logger.info(f"Permanently deleted user: {user_email}")

        except Exception as e:
            logger.error(f"Failed to purge user {user.id}: {str(e)}")

    return f"Purged {purged_count} soft-deleted users."
