from django.db import models


class NepdoraVideo(models.Model):
    TYPE_CHOICES = (
        ("tutorial", "Tutorial"),
        ("plugin", "Plugin"),
    )
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=TYPE_CHOICES, db_index=True)
    video_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["type", "created_at"]),
        ]

    def __str__(self):
        return self.title
