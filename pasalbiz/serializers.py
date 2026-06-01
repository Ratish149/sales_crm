from django.db import connection
from django.utils import timezone
from django.utils.text import slugify
from django_tenants.utils import schema_context
from rest_framework import serializers

from product.models import Product
from tenants.models import Client
from website.models import SiteConfig


class StoreListSerializer(serializers.ModelSerializer):
    tenant_id = serializers.SerializerMethodField()
    base_url = serializers.CharField(read_only=True)
    api_root = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()
    store_slug = serializers.SerializerMethodField()
    store_description = serializers.SerializerMethodField()
    store_logo = serializers.SerializerMethodField()
    seller_id = serializers.SerializerMethodField()
    seller_location = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    last_indexed_at = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            "tenant_id",
            "base_url",
            "api_root",
            "status",
            "store_name",
            "store_slug",
            "store_description",
            "store_logo",
            "seller_id",
            "seller_location",
            "product_count",
            "last_indexed_at",
        ]

    def get_tenant_id(self, obj):
        return str(obj.id)

    def get_api_root(self, obj):
        return "api"

    def get_status(self, obj):
        return "active" if obj.is_plan_active() else "blocked"

    def get_last_indexed_at(self, obj):
        try:
            with schema_context(obj.schema_name):
                newest = (
                    Product.objects
                    .filter(status="active")
                    .order_by("-updated_at")
                    .first()
                )
                if newest:
                    return newest.updated_at.isoformat()
        except Exception:
            pass
        return None

    def get_store_name(self, obj):
        try:
            with schema_context(obj.schema_name):
                config = SiteConfig.objects.first()
                if config and config.business_name:
                    return config.business_name
        except Exception:
            pass
        return obj.name

    def get_store_slug(self, obj):
        try:
            with schema_context(obj.schema_name):
                config = SiteConfig.objects.first()
                if config and config.business_name:
                    return slugify(config.business_name)
        except Exception:
            pass
        return slugify(obj.name)

    def get_store_description(self, obj):
        try:
            with schema_context(obj.schema_name):
                config = SiteConfig.objects.first()
                if config and config.business_details:
                    return config.business_details
        except Exception:
            pass
        return obj.description or ""

    def get_store_logo(self, obj):
        request = self.context.get("request")
        try:
            with schema_context(obj.schema_name):
                config = SiteConfig.objects.first()
                if config and config.logo:
                    url = config.logo.url
                    return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        if obj.template_image:
            url = obj.template_image.url
            return request.build_absolute_uri(url) if request else url
        return ""

    def get_seller_id(self, obj):
        return str(obj.owner_id) if obj.owner_id else ""

    def get_seller_location(self, obj):
        try:
            with schema_context(obj.schema_name):
                config = SiteConfig.objects.first()
                if config and config.address:
                    return config.address
        except Exception:
            pass
        return ""

    def get_product_count(self, obj):
        try:
            with schema_context(obj.schema_name):
                return Product.objects.filter(status="active").count()
        except Exception:
            return 0


class StorefrontProductSerializer(serializers.ModelSerializer):
    external_id = serializers.SerializerMethodField()
    tenant_id = serializers.SerializerMethodField()
    permalink = serializers.SerializerMethodField()
    sku = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    regular_price = serializers.SerializerMethodField()
    sale_price = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    indexed_at = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "external_id",
            "tenant_id",
            "name",
            "slug",
            "permalink",
            "sku",
            "description",
            "attributes",
            "price",
            "regular_price",
            "sale_price",
            "images",
            "categories",
            "tags",
            "in_stock",
            "indexed_at",
        ]

    def get_external_id(self, obj):
        return str(obj.id)

    def get_tenant_id(self, obj):
        tenant = getattr(connection, "tenant", None)
        if tenant and getattr(tenant, "id", None):
            return str(tenant.id)
        return ""

    def get_permalink(self, obj):
        tenant = getattr(connection, "tenant", None)
        if tenant:
            # 1. Try the primary domain first
            primary_domain = tenant.get_primary_domain()
            if primary_domain:
                protocol = "https"
                return f"{protocol}://{primary_domain.domain}/product/{obj.slug}/"

            # 2. Fall back to schemaname.nepdora.com style domain
            from tenants.models import Domain

            nepdora_domain = Domain.objects.filter(
                tenant=tenant, domain__startswith=f"{tenant.schema_name}."
            ).first()
            if nepdora_domain:
                return f"https://{nepdora_domain.domain}/product/{obj.slug}/"

            # 3. Last resort: use base_url from the Client model
            if hasattr(tenant, "base_url") and tenant.base_url:
                return f"{tenant.base_url}/product/{obj.slug}/"

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(f"/product/{obj.slug}/")
        return f"/product/{obj.slug}/"

    def get_sku(self, obj):
        return obj.id

    def get_attributes(self, obj):
        return {}

    def get_price(self, obj):
        return f"{obj.discounted_price:.2f}"

    def get_regular_price(self, obj):
        return f"{obj.price:.2f}"

    def get_sale_price(self, obj):
        if obj.discounted_price < obj.price:
            return f"{obj.discounted_price:.2f}"
        return None

    def get_images(self, obj):
        request = self.context.get("request")
        images = []
        if obj.thumbnail_image:
            url = obj.thumbnail_image.url
            images.append({
                "src": request.build_absolute_uri(url) if request else url,
                "alt": obj.thumbnail_alt_description or "",
                "position": 1,
            })
        try:
            for i, prod_img in enumerate(
                obj.images.all(), start=2 if obj.thumbnail_image else 1
            ):
                if prod_img.image:
                    url = prod_img.image.url
                    images.append({
                        "src": request.build_absolute_uri(url) if request else url,
                        "alt": "",
                        "position": i,
                    })
        except Exception:
            pass
        return images

    def get_categories(self, obj):
        categories = []
        if obj.category:
            categories.append({
                "id": obj.category.id,
                "name": obj.category.name,
                "slug": obj.category.slug,
            })
        if obj.sub_category:
            categories.append({
                "id": obj.sub_category.id,
                "name": obj.sub_category.name,
                "slug": obj.sub_category.slug,
            })
        return categories

    def get_tags(self, obj):
        return []

    def get_in_stock(self, obj):
        if obj.track_stock and obj.stock is not None:
            return obj.stock > 0
        return True

    def get_indexed_at(self, obj):
        return timezone.now().isoformat()
