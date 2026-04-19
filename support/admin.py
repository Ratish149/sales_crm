from django.contrib import admin
from tinymce.widgets import TinyMCE

from .models import (
    FAQ,
    Contact,
    FAQCategory,
    NepdoraTestimonial,
    Showcase,
    VideoTestimonial,
)

# Register your models here.


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "created_at", "updated_at")


@admin.register(NepdoraTestimonial)
class NepdoraTestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "designation", "created_at", "updated_at")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone_number", "created_at", "updated_at")


@admin.register(Showcase)
class ShowcaseAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "description":
            return db_field.formfield(widget=TinyMCE())
        return super().formfield_for_dbfield(db_field, **kwargs)


@admin.register(VideoTestimonial)
class VideoTestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "description":
            return db_field.formfield(widget=TinyMCE())
        return super().formfield_for_dbfield(db_field, **kwargs)
