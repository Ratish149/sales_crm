import re

import pandas as pd
from django.http import HttpResponse
from django_filters import rest_framework as django_filters
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from rest_framework import filters, generics, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from customer.utils import get_customer_from_request

from .models import (
    Category,
    Product,
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
    ProductImageSerializer,
    ProductReviewDetailSerializer,
    ProductReviewSerializer,
    ProductSerializer,
    ProductSmallSerializer,
    SubCategoryDetailSerializer,
    SubCategorySerializer,
    WishlistSerializer,
)
from .utils import download_image_from_url, safe_value

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


class SubCategoryListCreateView(generics.ListCreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter]
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


class ProductImageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer


class ProductFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(
        field_name="category__slug", lookup_expr="iexact"
    )
    sub_category = django_filters.CharFilter(
        field_name="sub_category__slug", lookup_expr="iexact"
    )

    class Meta:
        model = Product
        fields = ["category", "sub_category"]


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ProductFilterSet
    search_fields = ["name"]

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
                Product.objects.select_related("category", "sub_category")
                .prefetch_related(
                    "images",
                    "variants__option_values__option",
                    "productoption_set__productoptionvalue_set",
                )
                .only(
                    "id",
                    "name",
                    "slug",
                    "description",
                    "price",
                    "market_price",
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

    def get_queryset(self):
        """
        Optimized queryset for single product retrieval with all necessary relations
        """
        if self.request.method == "GET":
            # For single product GET - prefetch all related data
            return (
                Product.objects.select_related("category", "sub_category")
                .prefetch_related(
                    "images",
                    "variants__option_values__option",
                    "productoption_set__productoptionvalue_set",
                )
                .only(
                    "id",
                    "name",
                    "slug",
                    "description",
                    "price",
                    "market_price",
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


class ProductReviewFilter(django_filters.FilterSet):
    rating = django_filters.NumberFilter(field_name="rating", lookup_expr="exact")

    class Meta:
        model = ProductReview
        fields = ["rating"]


class ProductReviewView(generics.ListCreateAPIView):
    queryset = (
        ProductReview.objects.only(
            "id", "product", "user", "review", "rating", "created_at"
        )
        .select_related("product", "user")
        .order_by("-created_at")
    )
    serializer_class = ProductReviewSerializer
    pagination_class = CustomPagination
    filter_backends = [
        django_filters.DjangoFilterBackend,
    ]
    filterset_class = ProductReviewFilter

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
        if not self.request.user.is_authenticated:
            raise serializers.ValidationError(
                "User must be authenticated to create a review."
            )
        user = get_customer_from_request(self.request)
        serializer.save(user=user)


class ProductReviewRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductReview.objects.only(
        "id", "product", "user", "review", "rating", "created_at", "updated_at"
    ).select_related("product", "user")
    serializer_class = ProductReviewSerializer
    lookup_field = "id"


class WishlistListCreateView(generics.ListCreateAPIView):
    queryset = Wishlist.objects.only(
        "id", "user", "product", "created_at", "updated_at"
    ).select_related("user", "product")
    serializer_class = WishlistSerializer

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
        # Create a workbook and select the active worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Product Template"

        # Define headers based on your model and serializer
        headers = [
            "name",
            "description",
            "price",
            "market_price",
            "track_stock",
            "stock",
            "weight",
            "thumbnail_image",
            "thumbnail_image_aly_description",
            "category",
            "subcategory",
            "is_popular",
            "is_featured",
            "status",
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

        # Write headers
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

        # Get actual data from database for dropdowns
        from .models import Category, SubCategory

        categories = Category.objects.all()
        subcategories = SubCategory.objects.select_related("category").all()

        # Sample category and subcategory names for the template
        sample_category = (
            categories.first().name if categories.exists() else "Electronics"
        )
        sample_subcategory = (
            subcategories.first().name if subcategories.exists() else "Mobile"
        )

        # Add sample data row (main product row)
        sample_data = [
            "productname",
            "product description",
            100,
            100,
            "TRUE",
            15,
            "45g",
            "image url",
            "alt description",
            sample_category,
            sample_subcategory,
            "TRUE",
            "FALSE",
            "active",
            "Color",
            "Green",
            "Size",
            "S",
            "",
            "",
            80,
            10,
            "image url",
            "Meta Title",
            "Meta Description",
        ]

        for col, value in enumerate(sample_data, 1):
            ws.cell(row=2, column=col, value=value)

        # Add additional variant row (empty except for variant columns)
        variant_only_data = [
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Blue",
            "",
            "M",
            "",
            "",
            85,
            15,
            "variant_image_url",
            "",
            "",
        ]

        for col, value in enumerate(variant_only_data, 1):
            ws.cell(row=3, column=col, value=value)

        # Add more variant examples
        additional_variants = [
            # Color: Blue, Size: L
            [
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "Blue",
                "",
                "L",
                "",
                "",
                90,
                20,
                "variant_image_url_2",
                "",
                "",
            ],
            # Color: Red, Size: S
            [
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "Red",
                "",
                "S",
                "",
                "",
                85,
                12,
                "variant_image_url_3",
                "",
                "",
            ],
        ]

        for row_num, variant_data in enumerate(additional_variants, 4):
            for col, value in enumerate(variant_data, 1):
                ws.cell(row=row_num, column=col, value=value)

        # Add data validation for dropdown fields
        self._add_data_validations(ws, categories, subcategories)

        # Auto-adjust column widths for better readability
        self._adjust_column_widths(ws)

        # Create HTTP response
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            'attachment; filename="product_bulk_upload_template.xlsx"'
        )

        wb.save(response)
        return response

    def _add_data_validations(self, ws, categories, subcategories):
        """Add data validation for dropdown fields with dynamic data from database"""

        # Boolean fields validation - track_stock
        bool_validation_track = DataValidation(
            type="list",
            formula1='"TRUE,FALSE"',
            allow_blank=True,
            showErrorMessage=True,
            errorTitle="Invalid boolean value",
            error="Please select either TRUE or FALSE",
        )
        ws.add_data_validation(bool_validation_track)
        bool_validation_track.add("E2:E1048576")  # track_stock

        # Boolean fields validation - is_popular
        bool_validation_popular = DataValidation(
            type="list",
            formula1='"TRUE,FALSE"',
            allow_blank=True,
            showErrorMessage=True,
            errorTitle="Invalid boolean value",
            error="Please select either TRUE or FALSE",
        )
        ws.add_data_validation(bool_validation_popular)
        bool_validation_popular.add("L2:L1048576")  # is_popular

        # Boolean fields validation - is_featured
        bool_validation_featured = DataValidation(
            type="list",
            formula1='"TRUE,FALSE"',
            allow_blank=True,
            showErrorMessage=True,
            errorTitle="Invalid boolean value",
            error="Please select either TRUE or FALSE",
        )
        ws.add_data_validation(bool_validation_featured)
        bool_validation_featured.add("M2:M1048576")  # is_featured

        # Status validation
        status_validation = DataValidation(
            type="list",
            formula1='"active,draft,archived"',
            allow_blank=True,
            showErrorMessage=True,
            errorTitle="Invalid status",
            error="Please select from: active, draft, archived",
        )
        ws.add_data_validation(status_validation)
        status_validation.add("N2:N1048576")  # status

        # Category validation (dynamic from database)
        if categories.exists():
            # Create comma-separated list of category names
            category_names = [cat.name for cat in categories]
            category_formula = '"' + ",".join(category_names) + '"'

            cat_validation = DataValidation(
                type="list",
                formula1=category_formula,
                allow_blank=True,
                showErrorMessage=True,
                errorTitle="Invalid category",
                error=f"Please select from available categories: {', '.join(category_names)}",
            )
            ws.add_data_validation(cat_validation)
            cat_validation.add("J2:J1048576")  # category

        # Subcategory validation (dynamic from database) with category name
        if subcategories.exists():
            # Create formatted subcategory names: "Subcategory Name (Category Name)"
            subcategory_display_names = []
            subcategory_mapping = {}  # Store mapping for processing during upload

            for sub in subcategories:
                display_name = f"{sub.name} ({sub.category.name})"
                subcategory_display_names.append(display_name)
                subcategory_mapping[display_name] = (
                    sub.name
                )  # Store original name for lookup

            # Store the mapping in the workbook for later use during upload processing
            # This would need to be handled in your bulk upload view
            subcategory_formula = '"' + ",".join(subcategory_display_names) + '"'

            subcat_validation = DataValidation(
                type="list",
                formula1=subcategory_formula,
                allow_blank=True,
                showErrorMessage=True,
                errorTitle="Invalid subcategory",
                error="Please select from available subcategories",
            )
            ws.add_data_validation(subcat_validation)
            subcat_validation.add("K2:K1048576")  # subcategory

    def _adjust_column_widths(self, ws):
        """Adjust column widths for better readability"""
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
            "K": 25,  # subcategory (wider to accommodate category name)
            "L": 12,  # is_popular
            "M": 12,  # is_featured
            "N": 10,  # status
            "O": 15,  # option1 name
            "P": 15,  # option1 values
            "Q": 15,  # option2 name
            "R": 15,  # option2 values
            "S": 15,  # option3 name
            "T": 15,  # option3 values
            "U": 15,  # variant price
            "V": 15,  # variant stock
            "W": 20,  # variant image
            "X": 20,  # meta title
            "Y": 25,  # meta description
        }

        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width


class BulkProductUploadView(APIView):
    serializer_class = BulkUploadSerializer
    """Upload Excel/CSV and create products"""

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            df = pd.read_excel(file)
            # Clean column names - remove extra spaces and make lowercase for consistency
            df.columns = [col.strip().lower() for col in df.columns]
        except Exception as e:
            return Response(
                {"error": f"Invalid Excel file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_products = {}
        current_product = None
        product_options = {}  # Store option names for each product

        for idx, row in df.iterrows():
            print(f"Processing row {idx}")

            product_name = safe_value(row.get("name"))

            # If we have a product name, it's either a new product or the main product row
            if product_name:
                # Check if product already exists in database
                if Product.objects.filter(name=product_name).exists():
                    continue

                current_product_key = product_name

                # Check if product already created in this upload
                if current_product_key not in created_products:
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

                    product = Product(
                        name=current_product_key,
                        description=safe_value(row.get("description"), ""),
                        price=safe_value(row.get("price"), 0),
                        market_price=safe_value(row.get("market_price")),
                        track_stock=safe_value(row.get("track_stock"), True),
                        stock=safe_value(row.get("stock"), 0),
                        weight=safe_value(row.get("weight")),
                        thumbnail_alt_description=safe_value(
                            row.get("thumbnail_image_aly_description"), ""
                        ),
                        category=category,
                        sub_category=sub_category,
                        is_popular=safe_value(row.get("is_popular"), False),
                        is_featured=safe_value(row.get("is_featured"), False),
                        status=safe_value(row.get("status"), "active"),
                        meta_title=safe_value(row.get("meta title"), ""),
                        meta_description=safe_value(row.get("meta description"), ""),
                    )

                    # Download thumbnail image
                    thumb_url = safe_value(row.get("thumbnail_image"))
                    if thumb_url:
                        thumb_file, thumb_filename = download_image_from_url(
                            thumb_url, upload_to="product_images"
                        )
                        if thumb_file:
                            product.thumbnail_image.save(
                                thumb_filename, thumb_file, save=False
                            )

                    product.save()

                    # Create product options based on the main row and store option names
                    option_names = self._create_product_options(product, row)
                    product_options[current_product_key] = option_names

                    created_products[current_product_key] = {
                        "product": product,
                        "options_created": True,
                    }
                    print(f"Created product: {product_name}")

                current_product = created_products[current_product_key]["product"]
                current_option_names = product_options[current_product_key]

            # Create variant for current product (even for empty name rows that continue variants)
            if current_product:
                variant = self._create_product_variant(
                    current_product, row, current_option_names
                )
                if variant:
                    print(f"Created variant for {current_product.name}")

        return Response(
            {
                "success": True,
                "message": f"Successfully processed {len(created_products)} products with variants",
            }
        )

    def _create_product_options(self, product, row):
        """Create product options from option columns and return option names"""
        # Clear existing options to avoid duplicates
        ProductOption.objects.filter(product=product).delete()

        option_names = {}

        # Dynamically find all option columns
        option_columns = {}
        for col_name in row.index:
            if "option" in str(col_name).lower() and "name" in str(col_name).lower():
                # Extract option number from column name
                # Handles: "option1 name", "option2 name", "option3 name", "option4 name", etc.
                col_str = str(col_name).lower()
                if "option" in col_str and "name" in col_str:
                    # Try to extract the number
                    match = re.search(r"option(\d+)\s*name", col_str)
                    if match:
                        option_num = int(match.group(1))
                        option_columns[option_num] = col_name

        # Process all found option columns
        for option_num, col_name in sorted(option_columns.items()):
            option_name = safe_value(row.get(col_name))
            # Find the corresponding values column
            values_col_name = f"option{option_num} values"
            option_values_str = safe_value(row.get(values_col_name))

            if option_name:
                # Store the option name
                option_names[option_num] = option_name

                # Create the option
                option, created = ProductOption.objects.get_or_create(
                    product=product, name=option_name
                )

                # For the main product row, create the first option value if present
                if option_values_str:
                    ProductOptionValue.objects.get_or_create(
                        option=option, value=option_values_str
                    )

                print(f"Created option: {option_name} for product: {product.name}")

        return option_names

    def _create_product_variant(self, product, row, option_names):
        """Create product variant with option values using stored option names"""
        variant_price = safe_value(row.get("variant price"))
        variant_stock = safe_value(row.get("variant stock"))
        variant_image_url = safe_value(row.get("variant image"))

        # Skip if no variant data or if this is the main product row without variant-specific data
        if variant_price is None and variant_stock is None:
            return None

        # Use product price/stock as fallback
        if variant_price is None:
            variant_price = product.price
        if variant_stock is None:
            variant_stock = product.stock or 0

        variant = ProductVariant(
            product=product,
            price=variant_price,
            stock=variant_stock,
        )

        # Download variant image
        if variant_image_url:
            variant_file, variant_filename = download_image_from_url(
                variant_image_url, upload_to="variant_images"
            )
            if variant_file:
                variant.image.save(variant_filename, variant_file, save=False)

        variant.save()

        # Add option values to variant using the stored option names
        option_values_added = []
        for option_num, option_name in option_names.items():
            # For variant rows, use the stored option names
            values_col_name = f"option{option_num} values"
            option_value_str = safe_value(row.get(values_col_name))

            if option_value_str:
                # Find the option (should already exist from main row)
                option = ProductOption.objects.filter(
                    product=product, name=option_name
                ).first()

                if option:
                    # Find or create the option value
                    option_value, created = ProductOptionValue.objects.get_or_create(
                        option=option, value=option_value_str
                    )

                    # Add to variant
                    variant.option_values.add(option_value)
                    option_values_added.append(f"{option_name}: {option_value_str}")

        print(f"Created variant with options: {', '.join(option_values_added)}")
        return variant
