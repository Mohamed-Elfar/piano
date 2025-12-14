from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .models import (
    Category, Subcategory, HeroSlide, PromoBanner,
    Color, Product, CustomUser, Room, Style, PromoGridCategory,
    Cart,
    CartItem,
    Favorite,
    ProductImage,
    Review,
    # NEW IMPORTS
    Governorate, Area, Address, Coupon, Order, OrderItem,
)

User = get_user_model()


# --- USER SERIALIZERS ---
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'name', 'email', 'phone_number')


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=255, write_only=True, required=True)
    phone_number = serializers.CharField(max_length=15, write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'name', 'phone_number')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        username = validated_data['email']
        user = User.objects.create_user(
            username=username,
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name'),
            phone_number=validated_data.get('phone_number'),
        )
        return user


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['name'] = user.name
        token['email'] = user.email
        return token


# --- ROOMS AND STYLES SERIALIZERS ---
class RoomSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ['id', 'name', 'image']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class StyleSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Style
        fields = ['id', 'name', 'image']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


# --- PRODUCT AND CATALOG SERIALIZERS ---
class ParentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name']


class SubcategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    parent_category = ParentCategorySerializer(read_only=True)

    class Meta:
        model = Subcategory
        fields = ['id', 'name', 'image', 'parent_category']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class CategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    subcategories = SubcategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'subcategories']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class HeroSlideSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = HeroSlide
        fields = ['id', 'title', 'subtitle', 'image', 'button_text', 'button_link']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class PromoBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoBanner
        fields = ['end_date']


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name', 'hex_code']


class ProductImageSerializer(serializers.ModelSerializer):
    color_hex = serializers.CharField(source='color.hex_code', read_only=True, allow_null=True)

    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'color_hex']


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.email', read_only=True) # Changed from username to email
    
    class Meta:
        model = Review
        fields = ['id', 'user', 'rating', 'comment', 'created_at']
        read_only_fields = ['user', 'created_at']


class ProductSearchSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    sale_badge_image = serializers.SerializerMethodField()
    category = serializers.StringRelatedField()
    subcategory = serializers.StringRelatedField()
    colors = ColorSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'short_description',
            'original_price',
            'sale_price',
            'is_on_sale',
            'sale_badge_image',
            'rating',
            'image',
            'colors',
            'category',
            'subcategory',
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def get_sale_badge_image(self, obj):
        request = self.context.get('request')
        if obj.sale_badge_image and hasattr(obj.sale_badge_image, 'url'):
            return request.build_absolute_uri(obj.sale_badge_image.url) if request else obj.sale_badge_image.url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    colors = ColorSerializer(many=True, read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)
    styles = StyleSerializer(many=True, read_only=True)
    image = serializers.SerializerMethodField()
    sale_badge_image = serializers.SerializerMethodField()
    
    gallery_images = ProductImageSerializer(many=True, read_only=True)
    
    is_favorited = serializers.SerializerMethodField()
    
    reviews = ReviewSerializer(many=True, read_only=True)

    category_id = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=Category.objects.all(),
        required=True
    )
    subcategory_id = serializers.PrimaryKeyRelatedField(
        source='subcategory',
        queryset=Subcategory.objects.all(),
        required=False,
        allow_null=True
    )

    category = CategorySerializer(read_only=True)
    subcategory = SubcategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'short_description',
            'dimensions',
            'original_price',
            'sale_price',
            'is_on_sale',
            'sale_badge_image',
            'rating',
            'image',
            'gallery_images',
            'colors',
            'rooms',
            'styles',
            'is_active',
            'created_at',
            'category_id',
            'subcategory_id',
            'category',
            'subcategory',
            'is_favorited',
            'reviews',
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def get_sale_badge_image(self, obj):
        request = self.context.get('request')
        if obj.sale_badge_image and hasattr(obj.sale_badge_image, 'url'):
            return request.build_absolute_uri(obj.sale_badge_image.url) if request else obj.sale_badge_image.url
        return None
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Assumes the `Favorite` model is correctly related (prefetched in the view)
            return obj.favorite_set.filter(user=request.user).exists()
        return False
        
    def create(self, validated_data):
        # NOTE: If using a viewset, this logic might be better handled in perform_create/update
        gallery_images_data = self.context.get('view').request.FILES.getlist('gallery_images')
        
        product = super().create(validated_data)
        
        for image_data in gallery_images_data:
            ProductImage.objects.create(product=product, image=image_data)
        
        return product


# -----------------------
# New Serializer for Promo Grid
# -----------------------
class PromoGridCategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = PromoGridCategory
        fields = ['id', 'title', 'subtitle', 'image', 'background_color']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

# --- LOCATION SERIALIZERS (Nested Read-Only) ---
class AreaNestedSerializer(serializers.ModelSerializer):
    """Used for nested representation within UserAddressSerializer (minimal fields)."""
    shipping_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Area
        fields = ['id', 'name', 'shipping_cost']

class GovernorateNestedSerializer(serializers.ModelSerializer):
    """Used for nested representation within UserAddressSerializer (minimal fields)."""
    class Meta:
        model = Governorate
        fields = ['id', 'name']

class AreaSerializer(AreaNestedSerializer):
    """Full Area serializer, includes Governorate link."""
    governorate = GovernorateNestedSerializer(read_only=True)
    class Meta(AreaNestedSerializer.Meta):
        fields = AreaNestedSerializer.Meta.fields + ['governorate']

class GovernorateSerializer(GovernorateNestedSerializer):
    """Full Governorate serializer, includes nested areas."""
    areas = AreaSerializer(many=True, read_only=True)
    class Meta(GovernorateNestedSerializer.Meta):
        fields = GovernorateNestedSerializer.Meta.fields + ['areas']

# -----------------------
# 🎯 ADDRESS SERIALIZERS (For UserAddressViewSet)
# -----------------------
class UserAddressSerializer(serializers.ModelSerializer):
    """
    Serializer for CRUD operations on a user's saved addresses.
    Uses nested fields for read and PrimaryKey for write.
    """
    # Read-only nested representation
    area = AreaNestedSerializer(read_only=True)
    governorate = GovernorateNestedSerializer(source='area.governorate', read_only=True)
    
    # Write-only ID for creation/update (ID of the Area)
    # NOTE: The Area model already links to Governorate, so we only need Area ID.
    area_id = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), 
        source='area', 
        write_only=True
    )

    class Meta:
        model = Address
        fields = [
            'id', 
            'first_name', 
            'last_name', 
            'phone_number', 
            'street_address', 
            'apartment_details', 
            'area', 
            'governorate', 
            'area_id', 
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

# -----------------------
# ADDRESS SERIALIZER FOR CHECKOUT (ShippingAddressSerializer)
# -----------------------
class ShippingAddressSerializer(serializers.ModelSerializer):
    """
    Used *only* inside the CheckoutSerializer to capture the address snapshot.
    It expects the Area ID for validation and provides nested Area/Governorate names for confirmation.
    """
    # Write-only Field: Address requires Area ID
    area_id = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(), 
        source='area', 
        write_only=True
    )
    
    # Read-only confirmation fields (pulled from the Area object linked via source='area.governorate')
    governorate_name = serializers.CharField(source='area.governorate.name', read_only=True)
    area_name = serializers.CharField(source='area.name', read_only=True)

    class Meta:
        model = Address
        fields = [
            # 🎯 CRITICAL FIX: Add all fields necessary to create a new Address instance
            'first_name', 
            'last_name', 
            'phone_number', 
            'street_address', 
            'apartment_details', 
            # End of critical fields
            'id', 
            'area_id', 
            'governorate_name', 
            'area_name'
        ]
        read_only_fields = ['id', 'governorate_name', 'area_name']

# --- COUPON SERIALIZER ---
class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_percent', 'valid_from', 'valid_to', 'is_active']
        read_only_fields = ['discount_percent', 'valid_from', 'valid_to', 'is_active']

# --- SHOPPING CART SERIALIZERS ---
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSearchSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True,
        source='product'
    )

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    cart_subtotal = serializers.SerializerMethodField() 
    
    coupon_code = serializers.CharField(source='coupon.code', read_only=True, allow_null=True)
    coupon_discount_percent = serializers.IntegerField(source='coupon.discount_percent', read_only=True, allow_null=True)
    
    coupon_discount_amount = serializers.SerializerMethodField() 
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'cart_subtotal', 'coupon_code', 'coupon_discount_percent', 'coupon_discount_amount', 'created_at']

    def get_cart_subtotal(self, obj):
        return obj.get_cart_total()

    def get_coupon_discount_amount(self, obj):
        """Calculates the money discount based on subtotal and coupon percent."""
        if not obj.coupon:
            return Decimal('0.00')
        
        subtotal = obj.get_cart_total()
        discount_percent = Decimal(obj.coupon.discount_percent) / Decimal(100)
        discount_amount = subtotal * discount_percent
        return discount_amount.quantize(Decimal('0.01'))


# --- ORDER SERIALIZERS ---

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for displaying items within a submitted order (a historical record)."""
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_image = serializers.SerializerMethodField()

    def get_product_image(self, obj):
        try:
            if obj.product and getattr(obj.product, 'image', None):
                request = self.context.get('request')
                url = obj.product.image.url
                if request is not None:
                    return request.build_absolute_uri(url)
                return url
        except Exception:
            return None

    class Meta:
        model = OrderItem
        fields = ['product_id', 'product_name', 'product_image', 'quantity', 'price_at_purchase', 'get_total_price']
        read_only_fields = fields # All are read-only when viewing an order

class OrderListSerializer(serializers.ModelSerializer):
    """Simplified Serializer for listing a user's past orders."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 
            'final_total', 
            'status', 
            'status_display',
            'created_at'
        ]
        read_only_fields = fields

class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed Serializer for viewing a single complete order."""
    items = OrderItemSerializer(many=True, read_only=True)
    # The address stored on the Order is used for the snapshot
    shipping_address = ShippingAddressSerializer(read_only=True) 
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 
            'user', 
            'shipping_address',
            'cart_subtotal', 
            'shipping_cost', 
            'coupon_discount', 
            'final_total',
            'coupon_code_used',
            'payment_method',
            'payment_status',
            'transaction_id',
            'status',
            'status_display',
            'created_at',
            'items', # Nested order items
        ]
        read_only_fields = fields # All are read-only when retrieving a placed order

# --- CHECKOUT SERIALIZER ---
class CheckoutSerializer(serializers.Serializer):
    """
    Main serializer for receiving the final order submission payload from the frontend.
    It handles validation and the entire Order creation process.
    """
    # This uses the corrected ShippingAddressSerializer
    shipping_address = ShippingAddressSerializer(help_text="Nested fields for the shipping address.")
    
    payment_method = serializers.CharField(
        max_length=50, 
        help_text="e.g., 'Cash on Delivery', 'Credit Card', 'PayPal'."
    )
    # 💡 Coupon code removed as it should be applied to the Cart *before* checkout.
    
    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        
        # 1. Pop nested data
        address_data = validated_data.pop('shipping_address')
        payment_method = validated_data.pop('payment_method')
        
        # --- Pre-Order Checks and Calculations ---
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError("User does not have an active cart.")
            
        if not cart.items.exists():
            raise serializers.ValidationError("Cannot checkout on an empty cart.")

        # Recalculate everything at the time of purchase
        cart_subtotal = cart.get_cart_total()

        # 2. Handle Shipping Address
        # We create the Address model instance right here
        # The area is validated by the nested serializer and passed as the Area object
        shipping_address = Address.objects.create(user=user, **address_data)
        
        # 3. Calculate Shipping Cost
        # Since Address now only links to Area, we access shipping_cost through Area
        shipping_cost = shipping_address.area.shipping_cost if shipping_address.area else Decimal('0.00')

        # 4. Handle Coupon/Discount
        coupon = None
        coupon_discount_amount = Decimal('0.00')
        
        # Source of truth for coupon is the cart object
        if cart.coupon and cart.coupon.is_active and cart.coupon.valid_to >= timezone.now():
            coupon = cart.coupon
            discount_percent = Decimal(coupon.discount_percent) / Decimal(100)
            coupon_discount_amount = cart_subtotal * discount_percent
        
        final_total = (cart_subtotal + shipping_cost) - coupon_discount_amount
        
        if final_total < Decimal('0.00'):
            final_total = Decimal('0.00')
        
        # Quantize all decimals for clean storage
        cart_subtotal = cart_subtotal.quantize(Decimal('0.01'))
        shipping_cost = shipping_cost.quantize(Decimal('0.01'))
        coupon_discount_amount = coupon_discount_amount.quantize(Decimal('0.01'))
        final_total = final_total.quantize(Decimal('0.01'))


        # 5. Create the Order
        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            cart_subtotal=cart_subtotal,
            shipping_cost=shipping_cost,
            coupon_discount=coupon_discount_amount,
            coupon_code_used=coupon.code if coupon else None,
            final_total=final_total,
            payment_method=payment_method,
            status='PENDING' 
        )
        
        # 6. Create Order Items (The snapshot)
        order_items = []
        for cart_item in cart.items.select_related('product').all():
            order_items.append(
                OrderItem(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    quantity=cart_item.quantity,
                    price_at_purchase=cart_item.product.get_current_price()
                )
            )
        OrderItem.objects.bulk_create(order_items)
            
        # 7. Clear/Deactivate the User's Cart
        cart.delete() # Clears the cart and all its items

        return order # CRITICAL: Ensure the created order object is returned

# --- FAVORITE SERIALIZERS ---
class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductSearchSerializer(read_only=True)
    # Expose the model's `created_at` timestamp under the API-friendly
    # name `added_at` so front-end code that expects `added_at` keeps working.
    added_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'product', 'added_at']


# --- USER PROFILE SERIALIZER ---
class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializers to display a user's profile, including their favorited products and orders.
    """
    favorites = FavoriteSerializer(many=True, read_only=True)
    # Corrected: Use source='order_set' to match the database reverse relationship name
    orders = OrderListSerializer(source='order_set', many=True, read_only=True) 
    
    class Meta:
        model = CustomUser
        # 🌟 FIX: Removed 'username' as it likely doesn't exist on CustomUser
        # if email is used as the USERNAME_FIELD.
        fields = ['id', 'email', 'name', 'phone_number', 'favorites', 'orders']