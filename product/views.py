import io
import re

import pandas as pd
from django.db.models import Avg
from django.http import FileResponse
from django_filters import rest_framework as django_filters
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from rest_framework import filters, generics, permissions, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from customer.authentication import CustomerJWTAuthentication
from customer.utils import get_customer_from_request
from sales_crm.authentication import TenantJWTAuthentication

from .models import (
    Category,
    PricingMetric,
    Product,
    ProductComposition,
    ProductImage,
    ProductOption,
    ProductOptionValue,
    ProductReview,
    ProductVariant,
    SubCategory,
    Wishlist,
)
from .serializers import (
    BulkUploadSerializer,
    CategorySerializer,
    PricingMetricSerializer,
    ProductCompositionSerializer,
    ProductImageSerializer,
    ProductReviewDetailSerializer,
    ProductReviewSerializer,
    ProductSerializer,
    ProductSmallSerializer,
    ProductVariantAsProductSerializer,
    SubCategoryDetailSerializer,
    SubCategorySerializer,
    WishlistSerializer,
)
from .utils import (
    download_image_from_url,
    extract_images_from_zip,
    process_image_field,
    safe_value,
)

# Create your views here.


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class CategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "slug"


class SubCategoryFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(
        field_name="category__id", lookup_expr="iexact"
    )

    class Meta:
        model = SubCategory
        fields = ["category"]


class SubCategoryListCreateView(generics.ListCreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter, django_filters.DjangoFilterBackend]
    filterset_class = SubCategoryFilterSet
    search_fields = ["name"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SubCategorySerializer
        return SubCategoryDetailSerializer


class SubCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SubCategorySerializer
        return SubCategoryDetailSerializer


class ProductImageListCreateView(generics.ListCreateAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class ProductImageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]


class ProductFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(
        field_name="category__slug", lookup_expr="iexact"
    )
    sub_category = django_filters.CharFilter(
        field_name="sub_category__slug", lookup_expr="iexact"
    )
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    is_popular = django_filters.BooleanFilter(field_name="is_popular")
    is_featured = django_filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = Product
        fields = [
            "category",
            "sub_category",
            "min_price",
            "max_price",
            "is_popular",
            "is_featured",
        ]


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = CustomPagination
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductFilterSet
    ordering_fields = ["created_at", "price", "is_popular", "average_rating"]
    search_fields = ["name"]

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductSerializer
        return ProductSmallSerializer

    def get_queryset(self):
        """
        Optimized queryset with selective prefetching based on request method
        """
        if self.request.method == "GET":
            # For list view - optimized with prefetch and only
            return (
                Product.objects
                .select_related("category", "sub_category")
                .prefetch_related(
                    "images",
                    "variants__option_values__option",
                    "productoption_set__productoptionvalue_set",
                    "compositions__metric",
                )
                .annotate(average_rating=Avg("productreview__rating"))
                .only(
                    "id",
                    "name",
                    "slug",
                    "description",
                    "price",
                    "market_price",
                    "use_dynamic_pricing",
                    "base_making_charge",
                    "track_stock",
                    "stock",
                    "weight",
                    "thumbnail_image",
                    "thumbnail_alt_description",
                    "category_id",
                    "sub_category_id",
                    "is_popular",
                    "is_featured",
                    "status",
                    "meta_title",
                    "meta_description",
                    "created_at",
                    "updated_at",
                )
                .order_by("-created_at")
            )
        else:
            # For POST requests, return basic queryset
            return Product.objects.all()


class ProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = "slug"

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        """
        Optimized queryset for single product retrieval with all necessary relations
        """
        if self.request.method == "GET":
            # For single product GET - prefetch all related data
            return (
                Product.objects
                .select_related("category", "sub_category")
                .prefetch_related(
                    "images",
                    "variants__option_values__option",
                    "productoption_set__productoptionvalue_set",
                    "compositions__metric",
                )
                .only(
                    "id",
                    "name",
                    "slug",
                    "description",
                    "price",
                    "market_price",
                    "use_dynamic_pricing",
                    "base_making_charge",
                    "track_stock",
                    "stock",
                    "weight",
                    "thumbnail_image",
                    "thumbnail_alt_description",
                    "category_id",
                    "sub_category_id",
                    "is_popular",
                    "is_featured",
                    "status",
                    "meta_title",
                    "meta_description",
                    "created_at",
                    "updated_at",
                )
                .all()
            )
        else:
            # For PUT/PATCH/DELETE, use basic queryset
            return Product.objects.all()


class PricingMetricListCreateView(generics.ListCreateAPIView):
    queryset = PricingMetric.objects.all()
    serializer_class = PricingMetricSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]


class PricingMetricRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PricingMetric.objects.all()
    serializer_class = PricingMetricSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]


class ProductCompositionListCreateView(generics.ListCreateAPIView):
    queryset = ProductComposition.objects.all()
    serializer_class = ProductCompositionSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]


class ProductCompositionRetrieveUpdateDestroyView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = ProductComposition.objects.all()
    serializer_class = ProductCompositionSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]


class ProductReviewFilter(django_filters.FilterSet):
    rating = django_filters.NumberFilter(field_name="rating", lookup_expr="exact")

    class Meta:
        model = ProductReview
        fields = ["rating"]


class ProductReviewView(generics.ListCreateAPIView):
    queryset = (
        ProductReview.objects
        .only("id", "product", "user", "review", "rating", "created_at")
        .select_related("product", "user")
        .order_by("-created_at")
    )
    serializer_class = ProductReviewSerializer
    pagination_class = CustomPagination
    filter_backends = [
        django_filters.DjangoFilterBackend,
    ]
    filterset_class = ProductReviewFilter
    authentication_classes = [CustomerJWTAuthentication]

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ProductReviewDetailSerializer
        return ProductReviewSerializer

    def get_queryset(self):
        slug = self.request.query_params.get("slug")
        try:
            product = Product.objects.only("id").get(slug=slug)
            return ProductReview.objects.filter(product=product)
        except Product.DoesNotExist:
            return ProductReview.objects.all()

    def perform_create(self, serializer):
        user = get_customer_from_request(self.request)
        if not user:
            raise serializers.ValidationError(
                "User must be authenticated to create a review."
            )
        serializer.save(user=user)


class ProductReviewRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductReview.objects.only(
        "id", "product", "user", "review", "rating", "created_at", "updated_at"
    ).select_related("product", "user")
    serializer_class = ProductReviewSerializer
    authentication_classes = [CustomerJWTAuthentication]
    lookup_field = "id"

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


class WishlistListCreateView(generics.ListCreateAPIView):
    queryset = Wishlist.objects.only(
        "id", "user", "product", "created_at", "updated_at"
    ).select_related("user", "product")
    serializer_class = WishlistSerializer
    authentication_classes = [CustomerJWTAuthentication]

    def get_queryset(self):
        user = get_customer_from_request(self.request)
        if not user:
            return Wishlist.objects.none()
        return Wishlist.objects.filter(user=user)

    def perform_create(self, serializer):
        user = get_customer_from_request(self.request)
        if not user:
            raise serializers.ValidationError(
                "User must be authenticated to add to wishlist."
            )
        serializer.save(user=user)


class WishlistRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Wishlist.objects.only(
        "id", "user", "product", "created_at", "updated_at"
    ).select_related("user", "product")
    serializer_class = WishlistSerializer
    authentication_classes = [CustomerJWTAuthentication]
    lookup_field = "id"

    def get_object(self):
        try:
            user = get_customer_from_request(self.request)
            return Wishlist.objects.get(user=user)
        except Wishlist.DoesNotExist:
            return Response(
                {"message": "Wishlist not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def delete(self, request, *args, **kwargs):
        try:
            id = self.kwargs.get("id")
            user = get_customer_from_request(self.request)
            wishlist = Wishlist.objects.get(user=user, id=id)
            wishlist.delete()
            return Response(
                {"message": "Product removed from wishlist"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Wishlist.DoesNotExist:
            return Response(
                {"message": "Wishlist not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class DownloadProductSampleTemplateView(APIView):
    def get(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Product Template"

        from .models import Category, PricingMetric, SubCategory

        metrics = list(PricingMetric.objects.all())

        # ── Headers ──────────────────────────────────────────────────────────
        headers = [
            "name",  # A
            "description",  # B
            "price",  # C
            "market_price",  # D
            "track_stock",  # E
            "stock",  # F
            "weight",  # G
            "thumbnail_image",  # H
            "thumbnail_image_aly_description",  # I
            "category",  # J
            "subcategory",  # K
            "is_popular",  # L
            "is_featured",  # M
            "status",  # N
            "use_dynamic_pricing",  # O
            "base_making_charge",  # P
            "composition",  # Q  ← dropdown of metrics
            "quantity",  # R  ← numeric quantity
            "option1 name",  # S
            "option1 values",  # T
            "option2 name",  # U
            "option2 values",  # V
            "option3 name",  # W
            "option3 values",  # X
            "variant price",  # Y
            "variant stock",  # Z
            "variant image",  # AA
            "meta title",  # AB
            "meta description",  # AC
        ]

        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

        # ── Sample data ───────────────────────────────────────────────────────
        categories = Category.objects.all()
        subcategories = SubCategory.objects.select_related("category").all()

        sample_category = (
            categories.first().name if categories.exists() else "Electronics"
        )
        sample_subcategory = (
            subcategories.first().name if subcategories.exists() else "Mobile"
        )
        sample_metric = (
            f"{metrics[0].name} ({metrics[0].price_per_unit}/{metrics[0].unit})"
            if metrics
            else "Gold (13000.00/gram)"
        )

        # Row 2 — main product row with first composition and first variant
        sample_data = [
            "productname",  # A  name
            "product description",  # B  description
            100,  # C  price
            100,  # D  market_price
            "TRUE",  # E  track_stock
            15,  # F  stock
            "45g",  # G  weight
            "image url",  # H  thumbnail_image
            "alt description",  # I  thumbnail_image_aly_description
            sample_category,  # J  category
            sample_subcategory,  # K  subcategory
            "TRUE",  # L  is_popular
            "FALSE",  # M  is_featured
            "active",  # N  status
            "TRUE",  # O  use_dynamic_pricing
            0.00,  # P  base_making_charge
            sample_metric,  # Q  composition (first metric)
            5,  # R  quantity
            "Color",  # S  option1 name
            "Green",  # T  option1 values
            "Size",  # U  option2 name
            "S",  # V  option2 values
            "",  # W  option3 name
            "",  # X  option3 values
            80,  # Y  variant price
            10,  # Z  variant stock
            "image url",  # AA variant image
            "Meta Title",  # AB meta title
            "Meta Description",  # AC meta description
        ]

        for col, value in enumerate(sample_data, 1):
            ws.cell(row=2, column=col, value=value)

        # Row 3 — second composition row for the same product (only Q & R filled)
        second_metric = (
            f"{metrics[1].name} ({metrics[1].price_per_unit}/{metrics[1].unit})"
            if len(metrics) > 1
            else "Silver (190000.00/10)"
        )
        composition_row_2 = [""] * len(headers)
        composition_row_2[16] = second_metric  # Q (0-based index 16)
        composition_row_2[17] = 3  # R quantity
        for col, value in enumerate(composition_row_2, 1):
            ws.cell(row=3, column=col, value=value)

        # Rows 4-6 — variant-only rows (product columns blank, composition blank)
        def make_variant_row(opt1_val, opt2_val, v_price, v_stock, v_image):
            row = [""] * len(headers)
            row[19] = opt1_val  # T  option1 values
            row[21] = opt2_val  # V  option2 values
            row[24] = v_price  # Y  variant price
            row[25] = v_stock  # Z  variant stock
            row[26] = v_image  # AA variant image
            return row

        variant_rows = [
            make_variant_row("Blue", "M", 85, 15, "variant_image_url"),
            make_variant_row("Blue", "L", 90, 20, "variant_image_url_2"),
            make_variant_row("Red", "S", 85, 12, "variant_image_url_3"),
        ]

        for row_num, variant_data in enumerate(variant_rows, 4):
            for col, value in enumerate(variant_data, 1):
                ws.cell(row=row_num, column=col, value=value)

        # ── Validations & widths ──────────────────────────────────────────────
        self._add_data_validations(wb, ws, categories, subcategories, metrics)
        self._adjust_column_widths(ws)

        # ── Stream response ───────────────────────────────────────────────────
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        return FileResponse(
            buffer,
            as_attachment=True,
            filename="product_bulk_upload_template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _add_data_validations(self, wb, ws, categories, subcategories, metrics):
        """Add data validation for dropdown and numeric fields."""
        if "_dropdown_data" in wb.sheetnames:
            dropdown_ws = wb["_dropdown_data"]
        else:
            dropdown_ws = wb.create_sheet("_dropdown_data")
        dropdown_ws.sheet_state = "hidden"

        def add_bool_validation(cell_range):
            dv = DataValidation(
                type="list",
                formula1='"TRUE,FALSE"',
                allow_blank=True,
                showErrorMessage=True,
                errorTitle="Invalid value",
                error="Please select TRUE or FALSE",
            )
            ws.add_data_validation(dv)
            dv.add(cell_range)

        add_bool_validation("E2:E1048576")  # track_stock
        add_bool_validation("L2:L1048576")  # is_popular
        add_bool_validation("M2:M1048576")  # is_featured
        add_bool_validation("O2:O1048576")  # use_dynamic_pricing

        # Status
        status_dv = DataValidation(
            type="list",
            formula1='"active,draft,archived"',
            allow_blank=True,
            showErrorMessage=True,
            errorTitle="Invalid status",
            error="Please select from: active, draft, archived",
        )
        ws.add_data_validation(status_dv)
        status_dv.add("N2:N1048576")

        # Category (dynamic from DB)
        if categories.exists():
            cat_names = [c.name for c in categories]
            for i, name in enumerate(cat_names, 1):
                dropdown_ws.cell(row=i, column=1, value=name)
            cat_dv = DataValidation(
                type="list",
                formula1=f"'_dropdown_data'!$A$1:$A${len(cat_names)}",
                allow_blank=True,
                showErrorMessage=True,
                errorTitle="Invalid category",
                error="Please select from available categories",
            )
            ws.add_data_validation(cat_dv)
            cat_dv.add("J2:J1048576")

        # Subcategory (dynamic from DB)
        if subcategories.exists():
            sub_names = [f"{s.name} ({s.category.name})" for s in subcategories]
            for i, name in enumerate(sub_names, 1):
                dropdown_ws.cell(row=i, column=2, value=name)
            sub_dv = DataValidation(
                type="list",
                formula1=f"'_dropdown_data'!$B$1:$B${len(sub_names)}",
                allow_blank=True,
                showErrorMessage=True,
                errorTitle="Invalid subcategory",
                error="Please select from available subcategories",
            )
            ws.add_data_validation(sub_dv)
            sub_dv.add("K2:K1048576")

        # Composition column Q — dropdown of metrics: "Gold (13000.00/gram)"
        if metrics:
            metric_display_names = [
                f"{m.name} ({m.price_per_unit}/{m.unit})" for m in metrics
            ]
            for i, name in enumerate(metric_display_names, 1):
                dropdown_ws.cell(
                    row=i, column=3, value=name
                )  # Column C of hidden sheet
            comp_dv = DataValidation(
                type="list",
                formula1=f"'_dropdown_data'!$C$1:$C${len(metric_display_names)}",
                allow_blank=True,
                showErrorMessage=True,
                errorTitle="Invalid composition",
                error="Please select a valid metric from the dropdown",
            )
            ws.add_data_validation(comp_dv)
            comp_dv.add("Q2:Q1048576")  # composition column

        # Quantity column R — numeric validation
        qty_dv = DataValidation(
            type="decimal",
            operator="greaterThan",
            formula1="0",
            allow_blank=True,
            showErrorMessage=True,
            errorTitle="Invalid quantity",
            error="Enter a numeric quantity greater than 0",
        )
        ws.add_data_validation(qty_dv)
        qty_dv.add("R2:R1048576")  # quantity column

    def _adjust_column_widths(self, ws):
        """Adjust column widths for better readability."""
        column_widths = {
            "A": 15,  # name
            "B": 20,  # description
            "C": 10,  # price
            "D": 15,  # market_price
            "E": 12,  # track_stock
            "F": 10,  # stock
            "G": 10,  # weight
            "H": 20,  # thumbnail_image
            "I": 20,  # thumbnail_image_aly_description
            "J": 15,  # category
            "K": 25,  # subcategory
            "L": 12,  # is_popular
            "M": 12,  # is_featured
            "N": 10,  # status
            "O": 20,  # use_dynamic_pricing
            "P": 20,  # base_making_charge
            "Q": 30,  # composition (wider for metric display name)
            "R": 12,  # quantity
            "S": 15,  # option1 name
            "T": 15,  # option1 values
            "U": 15,  # option2 name
            "V": 15,  # option2 values
            "W": 15,  # option3 name
            "X": 15,  # option3 values
            "Y": 15,  # variant price
            "Z": 15,  # variant stock
            "AA": 20,  # variant image
            "AB": 20,  # meta title
            "AC": 25,  # meta description
        }
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width


# ─────────────────────────────────────────────────────────────────────────────


class BulkProductUploadView(APIView):
    serializer_class = BulkUploadSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TenantJWTAuthentication]
    """Upload Excel/CSV and create products."""

    def post(self, request):
        serializer = BulkUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data["file"]
        zip_file = serializer.validated_data.get("zip_file")

        try:
            images_from_zip = {}
            if zip_file:
                images_from_zip = extract_images_from_zip(zip_file)

            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            elif file.name.endswith((".xls", ".xlsx")):
                df = pd.read_excel(file)
            else:
                return Response(
                    {"error": "Unsupported file format. Please upload .csv or .xlsx"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            df.columns = [col.strip().lower() for col in df.columns]
        except Exception as e:
            return Response(
                {"error": f"Invalid file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .models import PricingMetric

        # Pre-load all metrics and map normalised display name → metric instance
        # e.g. "gold (13000.00/gram)" → <PricingMetric: Gold>
        all_metrics = list(PricingMetric.objects.all())
        metric_col_map = {
            f"{m.name} ({m.price_per_unit}/{m.unit})".strip().lower(): m
            for m in all_metrics
        }

        created_products = {}
        current_product = None
        current_option_names = {}
        product_options = {}
        # Accumulate composition rows per product before saving
        # { product_key: [(metric_instance, quantity), ...] }
        pending_compositions = {}

        for idx, row in df.iterrows():
            product_name = safe_value(row.get("name"))

            if product_name:
                # Flush pending compositions for previous product if any
                if current_product and current_product.pk in pending_compositions:
                    self._save_compositions(
                        current_product, pending_compositions.pop(current_product.pk)
                    )

                # Skip if product already exists in DB
                if Product.objects.filter(name=product_name).exists():
                    current_product = None
                    current_option_names = {}
                    continue

                current_product_key = product_name

                if current_product_key not in created_products:
                    # ── Resolve FK fields ─────────────────────────────────────
                    category_name = safe_value(row.get("category"))
                    sub_category_name = safe_value(row.get("subcategory"))

                    category = (
                        Category.objects.filter(name=category_name).first()
                        if category_name
                        else None
                    )
                    sub_category = (
                        SubCategory.objects.filter(name=sub_category_name).first()
                        if sub_category_name
                        else None
                    )

                    # ── use_dynamic_pricing (normalise to bool) ───────────────
                    raw_dynamic = safe_value(row.get("use_dynamic_pricing"), False)
                    if isinstance(raw_dynamic, str):
                        use_dynamic_pricing = raw_dynamic.strip().upper() == "TRUE"
                    else:
                        use_dynamic_pricing = bool(raw_dynamic)

                    # ── base_making_charge ────────────────────────────────────
                    base_making_charge = safe_value(row.get("base_making_charge"), 0.00)
                    try:
                        base_making_charge = (
                            float(base_making_charge)
                            if base_making_charge is not None
                            else 0.00
                        )
                    except (ValueError, TypeError):
                        base_making_charge = 0.00

                    # ── Build product dict ────────────────────────────────────
                    product_data = {
                        "name": current_product_key,
                        "description": safe_value(row.get("description"), ""),
                        "price": safe_value(row.get("price"), 0),
                        "market_price": safe_value(row.get("market_price")),
                        "track_stock": safe_value(row.get("track_stock"), True),
                        "stock": safe_value(row.get("stock"), 0),
                        "weight": safe_value(row.get("weight")),
                        "thumbnail_alt_description": safe_value(
                            row.get(
                                "thumbnail_image_alt_description",
                                row.get("thumbnail_image_aly_description"),
                            ),
                            "",
                        ),
                        "category": category,
                        "sub_category": sub_category,
                        "is_popular": safe_value(row.get("is_popular"), False),
                        "is_featured": safe_value(row.get("is_featured"), False),
                        "status": safe_value(row.get("status"), "active"),
                        "use_dynamic_pricing": use_dynamic_pricing,
                        "base_making_charge": base_making_charge,
                        "meta_title": safe_value(
                            row.get("meta_title", row.get("meta title")), ""
                        ),
                        "meta_description": safe_value(
                            row.get("meta_description", row.get("meta description")), ""
                        ),
                    }

                    product_data = {
                        k: v for k, v in product_data.items() if v is not None
                    }
                    product = Product(**product_data)

                    # ── Thumbnail image ───────────────────────────────────────
                    thumb_val = safe_value(row.get("thumbnail_image"))
                    if thumb_val:
                        if not str(thumb_val).startswith(("http://", "https://")):
                            thumb_file = process_image_field(thumb_val, images_from_zip)
                            if thumb_file:
                                product.thumbnail_image.save(
                                    thumb_file.name, thumb_file, save=False
                                )
                        else:
                            thumb_file, thumb_filename = download_image_from_url(
                                thumb_val, upload_to="product_images"
                            )
                            if thumb_file:
                                product.thumbnail_image.save(
                                    thumb_filename, thumb_file, save=False
                                )

                    try:
                        product.save()
                    except Exception as e:
                        return Response(
                            {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
                        )

                    # ── Options ───────────────────────────────────────────────
                    option_names = self._create_product_options(product, row)
                    product_options[current_product_key] = option_names

                    created_products[current_product_key] = {
                        "product": product,
                        "options_created": True,
                        "use_dynamic_pricing": use_dynamic_pricing,
                    }

                    # Initialise composition accumulator for this product
                    pending_compositions[product.pk] = []

                current_product = created_products[current_product_key]["product"]
                current_option_names = product_options[current_product_key]

            # ── Collect composition from this row (product row OR continuation row) ──
            if current_product:
                product_meta = next(
                    (
                        v
                        for v in created_products.values()
                        if v["product"].pk == current_product.pk
                    ),
                    None,
                )
                use_dynamic = (
                    product_meta["use_dynamic_pricing"] if product_meta else False
                )

                if use_dynamic:
                    composition_val = safe_value(row.get("composition"))
                    quantity_val = safe_value(row.get("quantity"))

                    if composition_val and quantity_val is not None:
                        normalised_comp = str(composition_val).strip().lower()
                        metric = metric_col_map.get(normalised_comp)
                        try:
                            quantity = float(quantity_val)
                        except (ValueError, TypeError):
                            quantity = None

                        if metric and quantity and quantity > 0:
                            pending_compositions.setdefault(
                                current_product.pk, []
                            ).append((metric, quantity))

                # Create variant for current product
                self._create_product_variant(
                    current_product, row, current_option_names, images_from_zip
                )

        # Flush compositions for the very last product in the file
        if current_product and current_product.pk in pending_compositions:
            self._save_compositions(
                current_product, pending_compositions.pop(current_product.pk)
            )

        return Response({
            "success": True,
            "message": f"Successfully processed {len(created_products)} products with variants",
        })

    # ── Composition save helper ───────────────────────────────────────────────
    def _save_compositions(self, product, composition_list):
        """
        Persist accumulated (metric, quantity) pairs as ProductComposition rows.
        Clears existing compositions first to allow clean re-imports.
        Only called when use_dynamic_pricing is True.
        """
        from .models import ProductComposition

        ProductComposition.objects.filter(product=product).delete()

        for metric, quantity in composition_list:
            ProductComposition.objects.create(
                product=product,
                metric=metric,
                quantity=quantity,
            )

    # ── Options helper ────────────────────────────────────────────────────────
    def _create_product_options(self, product, row):
        """Create product options from option columns and return option names."""
        ProductOption.objects.filter(product=product).delete()

        option_names = {}
        option_columns = {}

        for col_name in row.index:
            col_str = str(col_name).lower()
            match = re.search(r"option(\d+)\s*name", col_str)
            if match:
                option_columns[int(match.group(1))] = col_name

        for option_num, col_name in sorted(option_columns.items()):
            option_name = safe_value(row.get(col_name))
            values_col_name = f"option{option_num} values"
            option_values_str = safe_value(row.get(values_col_name))

            if option_name:
                option_names[option_num] = option_name
                option, _ = ProductOption.objects.get_or_create(
                    product=product, name=option_name
                )
                if option_values_str:
                    ProductOptionValue.objects.get_or_create(
                        option=option, value=option_values_str
                    )

        return option_names

    # ── Variant helper ────────────────────────────────────────────────────────
    def _create_product_variant(self, product, row, option_names, images_from_zip=None):
        """Create product variant with option values."""
        variant_price = safe_value(row.get("variant price"))
        variant_stock = safe_value(row.get("variant stock"))
        variant_image_val = safe_value(row.get("variant image"))

        if variant_price is None and variant_stock is None:
            return None

        variant = ProductVariant(
            product=product,
            price=variant_price if variant_price is not None else product.price,
            stock=variant_stock if variant_stock is not None else (product.stock or 0),
        )

        if variant_image_val:
            if images_from_zip and not str(variant_image_val).startswith((
                "http://",
                "https://",
            )):
                variant_file = process_image_field(variant_image_val, images_from_zip)
                if variant_file:
                    variant.image.save(variant_file.name, variant_file, save=False)
            else:
                variant_file, variant_filename = download_image_from_url(
                    variant_image_val, upload_to="variant_images"
                )
                if variant_file:
                    variant.image.save(variant_filename, variant_file, save=False)

        variant.save()

        for option_num, option_name in option_names.items():
            values_col_name = f"option{option_num} values"
            option_value_str = safe_value(row.get(values_col_name))
            if not option_value_str:
                continue

            option = ProductOption.objects.filter(
                product=product, name=option_name
            ).first()

            if option:
                option_value, _ = ProductOptionValue.objects.get_or_create(
                    option=option, value=option_value_str
                )
                variant.option_values.add(option_value)

        return variant


class ProductVariantFilterSet(django_filters.FilterSet):
    product = django_filters.NumberFilter(field_name="product__id")
    category = django_filters.CharFilter(
        field_name="product__category__slug", lookup_expr="iexact"
    )
    sub_category = django_filters.CharFilter(
        field_name="product__sub_category__slug", lookup_expr="iexact"
    )

    class Meta:
        model = ProductVariant
        fields = ["product", "category", "sub_category"]


class ProductVariantListCreateView(generics.ListCreateAPIView):
    queryset = (
        ProductVariant.objects
        .all()
        .select_related("product", "product__category", "product__sub_category")
        .prefetch_related("option_values__option")
    )
    serializer_class = ProductVariantAsProductSerializer
    pagination_class = CustomPagination
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductVariantFilterSet
    search_fields = ["product__name", "option_values__value"]
    ordering_fields = ["created_at", "price"]

    def get_authenticators(self):
        if self.request.method == "POST":
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()


class ProductVariantRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = (
        ProductVariant.objects
        .all()
        .select_related("product", "product__category", "product__sub_category")
        .prefetch_related("option_values__option")
    )
    serializer_class = ProductVariantAsProductSerializer

    def get_authenticators(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [TenantJWTAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated()]
        return super().get_permissions()
