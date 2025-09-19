from customer.serializers import CustomerSerializer
from rest_framework import serializers
from .models import Product, ProductImage, SubCategory, Category, ProductReview
from django.db.models import Avg


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'


class ProductImageSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class CategorySmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image']


class SubCategorySmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'slug', 'description', 'image']


class SubCategoryDetailSerializer(serializers.ModelSerializer):
    category = CategorySmallSerializer(read_only=True)

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'slug', 'description', 'image', 'category']


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSmallSerializer(
        many=True, read_only=True)
    sub_category = SubCategorySmallSerializer(read_only=True)
    category = CategorySmallSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, allow_null=True, required=False)
    sub_category_id = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), source='sub_category', write_only=True, allow_null=True, required=False)
    image_files = serializers.ListField(
        child=serializers.FileField(), source='images', write_only=True, required=False, allow_empty=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'price', 'market_price', 'stock', 'thumbnail_image', 'images',
                  'thumbnail_alt_description', 'category', 'sub_category', 'category_id', 'sub_category_id', 'is_popular', 'is_featured', 'created_at', 'updated_at', 'image_files']

    def create(self, validated_data):
        # Changed from 'image_files' to 'images' to match the source
        images_data = validated_data.pop('images', [])
        product = Product.objects.create(**validated_data)
        for image_data in images_data:
            ProductImage.objects.create(product=product, image=image_data)
        return product

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', [])
        instance = super().update(instance, validated_data)
        instance.images.all().delete()
        for image_data in images_data:
            ProductImage.objects.create(product=instance, image=image_data)
        return instance


class ProductSmallSerializer(serializers.ModelSerializer):
    sub_category = SubCategorySmallSerializer(read_only=True)
    category = CategorySmallSerializer(read_only=True)
    reviews_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    def get_reviews_count(self, obj):
        return ProductReview.objects.only('id').filter(product=obj).count()

    def get_average_rating(self, obj):
        return ProductReview.objects.only('id').filter(product=obj).aggregate(
            avg_rating=Avg('rating'))['avg_rating'] or 0

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'price', 'market_price', 'stock', 'thumbnail_image', 'thumbnail_alt_description',
                  'category', 'sub_category', 'is_popular', 'is_featured', 'created_at', 'updated_at', 'average_rating', 'reviews_count']


class ProductOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'price', 'market_price',
                  'thumbnail_image', 'thumbnail_alt_description']


class ProductReviewSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True,
        source='product'
    )
    product = ProductSmallSerializer(read_only=True)
    user = CustomerSerializer(read_only=True)

    class Meta:
        model = ProductReview
        fields = ['id', 'product_id', 'user_id', 'product', 'user', 'review',
                  'rating', 'created_at', 'updated_at']


class ProductReviewDetailSerializer(serializers.ModelSerializer):
    product = ProductSmallSerializer(read_only=True)
    user = CustomerSerializer(read_only=True)

    class Meta:
        model = ProductReview
        fields = ['id', 'product', 'user', 'review',
                  'rating', 'created_at']
