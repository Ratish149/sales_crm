from django.db import models

# Create your models here.


class IssueCategory(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Issue(models.Model):
    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("closed", "Closed"),
    )

    issue_category = models.ForeignKey(
        "IssueCategory", on_delete=models.CASCADE, null=True, blank=True
    )
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    priority = models.CharField(max_length=255, choices=PRIORITY_CHOICES, default="low")
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
