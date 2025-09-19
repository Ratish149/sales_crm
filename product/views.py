from customer.utils import get_customer_from_request
from rest_framework import generics, filters
from .models import Product, ProductImage, SubCategory, Category, ProductReview, Wishlist
from .serializers import ProductSerializer, ProductSmallSerializer, ProductImageSerializer, SubCategorySerializer, CategorySerializer, SubCategoryDetailSerializer, ProductReviewSerializer, ProductReviewDetailSerializer, WishlistSerializer
from rest_framework.pagination import PageNumberPagination
from django_filters import rest_framework as django_filters

# Create your views here.


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = CustomPagination


class CategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'


class SubCategoryListCreateView(generics.ListCreateAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SubCategorySerializer
        return SubCategoryDetailSerializer


class SubCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.request.method == 'POST':
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
        field_name='category__slug', lookup_expr='iexact')
    sub_category = django_filters.CharFilter(
        field_name='sub_category__slug', lookup_expr='iexact')

    class Meta:
        model = Product
        fields = ['category', 'sub_category']


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = CustomPagination
    filter_backends = [
        django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ProductFilterSet
    search_fields = ['name']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductSerializer
        return ProductSmallSerializer


class ProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'


class ProductReviewFilter(django_filters.FilterSet):
    rating = django_filters.NumberFilter(
        field_name='rating', lookup_expr='exact')

    class Meta:
        model = ProductReview
        fields = ['rating']


class ProductReviewView(generics.ListCreateAPIView):
    queryset = ProductReview.objects.only(
        'id', 'product', 'user', 'review', 'rating', 'created_at'
    ).select_related('product', 'user').order_by('-created_at')
    serializer_class = ProductReviewSerializer
    pagination_class = CustomPagination
    filter_backends = [django_filters.DjangoFilterBackend,]
    filterset_class = ProductReviewFilter

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductReviewDetailSerializer
        return ProductReviewSerializer

    def get_queryset(self):
        slug = self.request.query_params.get('slug')
        try:
            product = Product.objects.only('id').get(slug=slug)
            return ProductReview.objects.filter(product=product)
        except Product.DoesNotExist:
            return ProductReview.objects.all()

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise serializers.ValidationError(
                'User must be authenticated to create a review.')
        user = get_customer_from_request(self.request)
        serializer.save(user=user)


class ProductReviewRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductReview.objects.only(
        'id', 'product', 'user', 'review', 'rating', 'created_at', 'updated_at'
    ).select_related('product', 'user')
    serializer_class = ProductReviewSerializer
    lookup_field = 'id'


class WishlistListCreateView(generics.ListCreateAPIView):
    queryset = Wishlist.objects.only(
        'id', 'user', 'product', 'created_at', 'updated_at'
    ).select_related(
        'user',
        'product'
    )
    serializer_class = WishlistSerializer

    def get_queryset(self):
        user = get_customer_from_request(self.request)
        return Wishlist.objects.filter(user=user)

    def perform_create(self, serializer):
        user = get_customer_from_request(self.request)
        serializer.save(user=user)


class WishlistRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Wishlist.objects.only(
        'id', 'user', 'product', 'created_at', 'updated_at'
    ).select_related(
        'user',
        'product'
    )
    serializer_class = WishlistSerializer

    def get_object(self):
        try:
            user = get_customer_from_request(self.request)
            return Wishlist.objects.get(user=user)
        except Wishlist.DoesNotExist:
            raise Http404("Wishlist not found")

    def delete(self, request, *args, **kwargs):
        try:
            id = self.kwargs.get('id')
            user = get_customer_from_request(self.request)
            wishlist = Wishlist.objects.get(
                user=user, id=id)
            wishlist.delete()
            return Response({"message": "Product removed from wishlist"}, status=status.HTTP_204_NO_CONTENT)
        except Wishlist.DoesNotExist:
            raise Http404("Wishlist not found")
