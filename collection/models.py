from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class Collection(models.Model):
    """
    Stores the definition of a dynamic model created by the tenant.
    Includes default fields (name, content) plus custom field definitions in JSON format.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, null=True, blank=True)
    send_email = models.BooleanField(default=False)
    admin_email = models.EmailField(null=True, blank=True)

    # Default fields that are always present (like Framer CMS)
    default_fields = models.JSONField(
        default=dict,
        help_text="Default fields: {'name': {'type': 'text', 'required': true}, 'slug': {'type': 'text', 'required': false}, 'content': {'type': 'text', 'required': false}}",
    )

    # Custom fields defined by user
    fields = models.JSONField(
        default=list,
        help_text="Custom field definitions: [{'name': 'field_name', 'type': 'text', 'required': true, 'filterable': false}]",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Collection"
        verbose_name_plural = "Collections"

    def save(self, *args, **kwargs):
        """Auto-generate slug from name on save and set default fields"""
        if not self.slug:
            self.slug = slugify(self.name)

        # Set default fields if not already set
        if not self.default_fields:
            self.default_fields = {
                "name": {
                    "type": "text",
                    "required": True,
                    "filterable": True,
                    "searchable": True,
                    "model": None,
                },
                "slug": {
                    "type": "text",
                    "required": False,
                    "filterable": True,
                    "searchable": True,
                    "model": None,
                },
                "content": {
                    "type": "text",
                    "required": False,
                    "filterable": False,
                    "searchable": True,
                    "model": None,
                },
            }

        # Validate model references in default_fields and fields
        all_configs = list(self.default_fields.values())
        if self.fields:
            all_configs.extend(self.fields)

        for config in all_configs:
            model_ref = config.get("model")
            if model_ref:
                # Check if the referenced collection actually exists
                if not Collection.objects.filter(id=model_ref).exists():
                    raise ValidationError(
                        f"Referenced collection with ID '{model_ref}' does not exist."
                    )

        super().save(*args, **kwargs)

    def get_all_fields(self):
        """Get combined default and custom fields"""
        all_fields = []

        # Add default fields
        for field_name, field_config in self.default_fields.items():
            all_fields.append(
                {
                    "name": field_name,
                    "type": field_config.get("type", "text"),
                    "required": field_config.get("required", False),
                    "filterable": field_config.get("filterable", False),
                    "searchable": field_config.get("searchable", False),
                    "model": field_config.get("model", None),
                    "is_default": True,
                }
            )

        # Add custom fields
        for field in self.fields:
            field_copy = field.copy()
            field_copy["is_default"] = False
            all_fields.append(field_copy)

        return all_fields

    def __str__(self):
        return self.name


class CollectionData(models.Model):
    """
    Stores actual data instances for a dynamic model.
    All field values are stored in JSON format.
    """

    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="data_instances"
    )
    data = models.JSONField(
        help_text="Actual data values: {'field_name': 'value', ...}"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Collection Data"
        verbose_name_plural = "Collection Data"

    def __str__(self):
        return f"{self.collection.name} - Data #{self.id}"
