from django.contrib import admin

from .models import TeamMember, TeamMemberCategory

# Register your models here.
admin.site.register(TeamMember)
admin.site.register(TeamMemberCategory)

