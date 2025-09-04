from rest_framework import serializers
from .models import PopUp, PopUpForm, Banner, BannerImage


class PopUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = PopUp
        fields = '__all__'


class PopUpFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = PopUpForm
        fields = '__all__'


class BannerImageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)  # For updates

    class Meta:
        model = BannerImage
        fields = ['id', 'image', 'image_alt_description', 'link', 'is_active']


class BannerSerializer(serializers.ModelSerializer):
    images = BannerImageSerializer(many=True)

    class Meta:
        model = Banner
        fields = ['id', 'banner_type', 'is_active',
                  'created_at', 'updated_at', 'images']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        images_data = validated_data.pop('images')
        banner = Banner.objects.create(**validated_data)
        for image_data in images_data:
            BannerImage.objects.create(banner=banner, **image_data)
        return banner

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', [])
        instance.banner_type = validated_data.get(
            'banner_type', instance.banner_type)
        instance.is_active = validated_data.get(
            'is_active', instance.is_active)
        instance.save()

        # Update images
        existing_ids = [img.id for img in instance.images.all()]
        sent_ids = [img.get('id') for img in images_data if img.get('id')]

        # Delete images not in the request
        for img in instance.images.all():
            if img.id not in sent_ids:
                img.delete()

        # Create or update images
        for image_data in images_data:
            img_id = image_data.get('id', None)
            if img_id and img_id in existing_ids:
                # Update existing
                img = BannerImage.objects.get(id=img_id, banner=instance)
                for attr, value in image_data.items():
                    setattr(img, attr, value)
                img.save()
            else:
                # Create new
                BannerImage.objects.create(banner=instance, **image_data)

        return instance
