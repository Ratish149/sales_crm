from django.db import models


# Create your models here.
class Facebook(models.Model):
    user_token = models.TextField(blank=True, null=True)
    app_id = models.CharField(max_length=255, blank=True, null=True)
    app_secret = models.CharField(max_length=255, blank=True, null=True)
    page_id = models.CharField(max_length=255, blank=True, null=True)
    page_access_token = models.TextField(blank=True, null=True)
    page_name = models.CharField(max_length=255, blank=True, null=True)
    is_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.page_name}"

    class Meta:
        unique_together = ("page_id",)


class Conversation(models.Model):
    page = models.ForeignKey(
        Facebook, on_delete=models.CASCADE, related_name="conversations"
    )
    conversation_id = models.CharField(max_length=255, unique=True)
    participants = models.JSONField(blank=True, null=True)
    snippet = models.TextField(blank=True, null=True)
    updated_time = models.DateTimeField(blank=True, null=True)
    messages = models.JSONField(default=list, blank=True)
    last_synced = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.page.page_name} - {self.conversation_id}"
