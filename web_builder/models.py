from django.db import models


class AIUsageLog(models.Model):
    """
    Tracks token usage for AI operations.
    """

    tenant_name = models.CharField(
        max_length=255, help_text="Name of the tenant/workspace"
    )
    user_prompt = models.TextField(help_text="The user's original request")
    action_type = models.CharField(
        max_length=50, help_text="Type of action (e.g., analysis, generation)"
    )
    model_name = models.CharField(
        max_length=100, help_text="AI Model used (e.g., gemini-1.5-flash)"
    )

    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tenant_name} - {self.action_type} - {self.total_tokens} tokens"

    class Meta:
        ordering = ["-created_at"]
