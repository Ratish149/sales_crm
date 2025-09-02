from django.contrib import admin
from .models import IssueCategory, Issue

# Register your models here.

admin.site.register(IssueCategory)
admin.site.register(Issue)
