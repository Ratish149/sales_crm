from django.db import models


class APIKey(models.Model):
    key = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or self.key[:10] + "..."
