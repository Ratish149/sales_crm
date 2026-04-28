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

        # Fetch pricing metrics to build composition columns
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
            # composition columns added dynamically (Q onward)
        ]

        # Each metric gets its own quantity column: "Gold (500.00/gram)"
        composition_headers = [
            f"{m.name} ({m.price_per_unit}/{m.unit})" for m in metrics
        ]
        headers += composition_headers

        # Remaining fixed columns after compositions
        headers += [
            "option1 name",
            "option1 values",
            "option2 name",
            "option2 values",
            "option3 name",
            "option3 values",
            "variant price",
            "variant stock",
            "variant image",
            "meta title",
            "meta description",
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

        # Composition sample quantities (0 for each metric as placeholder)
        sample_composition_quantities = [0 for _ in metrics]

        sample_data = (
            [
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
                "FALSE",  # O  use_dynamic_pricing
                0.00,  # P  base_making_charge
            ]
            + sample_composition_quantities
            + [
                "Color",  #    option1 name
                "Green",  #    option1 values
                "Size",  #    option2 name
                "S",  #    option2 values
                "",  #    option3 name
                "",  #    option3 values
                80,  #    variant price
                10,  #    variant stock
                "image url",  #    variant image
                "Meta Title",  #    meta title
                "Meta Description",  #    meta description
            ]
        )

        for col, value in enumerate(sample_data, 1):
            ws.cell(row=2, column=col, value=value)

        # ── Variant-only rows ─────────────────────────────────────────────────
        num_fixed_before_compositions = 16  # columns A–P
        num_compositions = len(metrics)
        variant_col_offset = num_fixed_before_compositions + num_compositions

        def make_variant_row(option1_val, option2_val, v_price, v_stock, v_image):
            row = [""] * variant_col_offset
            row += [
                "",
                option1_val,
                "",
                option2_val,
                "",
                "",
                v_price,
                v_stock,
                v_image,
                "",
                "",
            ]
            return row

        variant_rows = [
            make_variant_row("Blue", "M", 85, 15, "variant_image_url"),
            make_variant_row("Blue", "L", 90, 20, "variant_image_url_2"),
            make_variant_row("Red", "S", 85, 12, "variant_image_url_3"),
        ]

        for row_num, variant_data in enumerate(variant_rows, 3):
            for col, value in enumerate(variant_data, 1):
                ws.cell(row=row_num, column=col, value=value)

        # ── Validations & widths ──────────────────────────────────────────────
        self._add_data_validations(
            wb, ws, categories, subcategories, metrics, num_fixed_before_compositions
        )
        self._adjust_column_widths(ws, metrics)

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

    @staticmethod
    def _col_letter(n):
        """Convert 1-based column index to Excel letter(s): 1→A, 27→AA, etc."""
        result = ""
        while n:
            n, rem = divmod(n - 1, 26)
            result = chr(65 + rem) + result
        return result

    def _add_data_validations(
        self, wb, ws, categories, subcategories, metrics, num_fixed_before_compositions
    ):
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

        # Composition metric columns — numeric validation (>= 0)
        for i, metric in enumerate(metrics):
            col_idx = num_fixed_before_compositions + 1 + i
            col_letter = self._col_letter(col_idx)
            num_dv = DataValidation(
                type="decimal",
                operator="greaterThanOrEqual",
                formula1="0",
                allow_blank=True,
                showErrorMessage=True,
                errorTitle=f"Invalid quantity for {metric.name}",
                error=f"Enter a numeric quantity (>= 0) for {metric.name}",
            )
            ws.add_data_validation(num_dv)
            num_dv.add(f"{col_letter}2:{col_letter}1048576")

    def _adjust_column_widths(self, ws, metrics):
        """Adjust column widths for better readability."""
        fixed_widths = {
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
        }
        for col, width in fixed_widths.items():
            ws.column_dimensions[col].width = width

        # Dynamic composition columns (Q onward)
        num_fixed = 16
        for i, metric in enumerate(metrics):
            col_letter = self._col_letter(num_fixed + 1 + i)
            header_len = len(f"{metric.name} ({metric.price_per_unit}/{metric.unit})")
            ws.column_dimensions[col_letter].width = max(18, header_len + 2)

        # Trailing option / variant / meta columns
        trailing_widths = [15, 15, 15, 15, 15, 15, 15, 15, 20, 20, 25]
        offset = num_fixed + len(metrics)
        for i, width in enumerate(trailing_widths):
            col_letter = self._col_letter(offset + 1 + i)
            ws.column_dimensions[col_letter].width = width


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

        # Pre-load all PricingMetrics and map normalised header → metric instance
        # Header format: "Gold (500.00/gram)" → normalised: "gold (500.00/gram)"
        from .models import PricingMetric

        all_metrics = list(PricingMetric.objects.all())
        metric_col_map = {
            f"{m.name} ({m.price_per_unit}/{m.unit})".strip().lower(): m
            for m in all_metrics
        }

        created_products = {}
        current_product = None
        current_option_names = {}
        product_options = {}

        for idx, row in df.iterrows():
            product_name = safe_value(row.get("name"))

            if product_name:
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

                    # ── use_dynamic_pricing (normalise bool) ──────────────────
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

                    # Remove None values to use model defaults
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

                    # ── Compositions: only when use_dynamic_pricing is True ────
                    if use_dynamic_pricing:
                        self._create_product_compositions(product, row, metric_col_map)

                    # ── Options ───────────────────────────────────────────────
                    option_names = self._create_product_options(product, row)
                    product_options[current_product_key] = option_names

                    created_products[current_product_key] = {
                        "product": product,
                        "options_created": True,
                    }

                current_product = created_products[current_product_key]["product"]
                current_option_names = product_options[current_product_key]

            # Create variant for current product
            if current_product:
                self._create_product_variant(
                    current_product, row, current_option_names, images_from_zip
                )

        return Response({
            "success": True,
            "message": f"Successfully processed {len(created_products)} products with variants",
        })

    # ── Composition helper ────────────────────────────────────────────────────
    def _create_product_compositions(self, product, row, metric_col_map):
        """
        Scan every column in the row; if the normalised column name matches a
        known metric header ("gold (500.00/gram)") and the cell has a value > 0,
        create a ProductComposition record.
        Only called when use_dynamic_pricing is True.
        """
        from .models import ProductComposition

        # Clear existing compositions to allow clean re-imports
        ProductComposition.objects.filter(product=product).delete()

        for col_name in row.index:
            normalised = str(col_name).strip().lower()
            metric = metric_col_map.get(normalised)
            if metric is None:
                continue

            quantity = safe_value(row.get(col_name))
            if quantity is None:
                continue

            try:
                quantity = float(quantity)
            except (ValueError, TypeError):
                continue

            if quantity <= 0:
                continue

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
