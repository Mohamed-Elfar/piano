from django.contrib import admin
from .models import (
    PromoBanner,
    Category,
    Subcategory,
    HeroSlide,
    Product,
    Color,
    CustomUser,
    Room,
    Style,
    PromoGridCategory,
    Cart,
    CartItem,
    Favorite,
    # --- Updated Imports ---
    Governorate,
    Area,
    Address,
    ProductImage,
    Review,
)

# -----------------------
# Product Image Inline
# -----------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'color') 
    raw_id_fields = ('color',)


# -----------------------
# Product Admin
# -----------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'subcategory',
        'original_price',
        'is_on_sale',
        'rating',
        'is_active'
    )
    list_filter = (
        'is_on_sale',
        'is_active',
        'category',
        'subcategory'
    )
    search_fields = ('name', 'description', 'short_description')

    filter_horizontal = ('colors', 'rooms', 'styles')
    
    inlines = [ProductImageInline]

    fields = (
        ('name', 'is_active'),
        ('category', 'subcategory'),
        'short_description',
        'description',
        'dimensions',
        'image',
        ('original_price', 'sale_price', 'is_on_sale'),
        'sale_badge_image',
        'rating',
        'colors',
        'rooms',
        'styles',
    )


# -----------------------
# Color Admin
# -----------------------
@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')


# -----------------------
# Promo Banner Admin
# -----------------------
@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = ('name', 'end_date', 'is_active')
    list_filter = ('is_active',)


# -----------------------
# Subcategory Inline for Category
# -----------------------
class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 1


# -----------------------
# Category Admin
# -----------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    fields = ('name', 'image')
    inlines = [SubcategoryInline]


# -----------------------
# Subcategory Admin
# -----------------------
@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent_category', 'image')
    list_filter = ('parent_category',)
    search_fields = ('name',)
    fields = ('name', 'image', 'parent_category')


# -----------------------
# Hero Slide Admin
# -----------------------
@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'order')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'order')


# -----------------------
# Favorite Inline for CustomUser
# -----------------------
class FavoriteInline(admin.TabularInline):
    model = Favorite
    extra = 0
    # ✅ FIX: Replaced 'added_at' with 'created_at' to resolve E035 error.
    readonly_fields = ('product', 'created_at')
    fields = ('product', 'created_at')
    can_delete = True
    verbose_name = "Favorite"
    verbose_name_plural = "Favorites"


# -----------------------
# Custom User Admin Inlines
# -----------------------
class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    # Area must be displayed, not governorate directly
    fields = ('area', 'street_address', 'is_default')
    # Use raw_id_fields for Area if you have many areas
    raw_id_fields = ('area',) 
    verbose_name = "User Address"
    verbose_name_plural = "User Addresses"


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'name', 'phone_number')
    search_fields = ('username', 'email', 'name')
    inlines = [FavoriteInline, AddressInline]


# -----------------------
# Register Room and Style Models
# -----------------------
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Style)
class StyleAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


# -----------------------
# Register Promo Grid Categories
# -----------------------
@admin.register(PromoGridCategory)
class PromoGridCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'image', 'background_color', 'is_active', 'order')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'order')
    search_fields = ('title', 'subtitle')
    fields = (
        ('title', 'subtitle'),
        ('image', 'background_color'),
        ('is_active', 'order')
    )


# -----------------------
# Shopping Cart Admin
# -----------------------
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product',)
    fields = ('product', 'quantity',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'user__email')
    inlines = [CartItemInline]
    readonly_fields = ('user', 'created_at', 'updated_at')

# -----------------------
# Location & Address Admin
# -----------------------

class AreaInline(admin.TabularInline):
    model = Area
    extra = 1
    fields = ('name', 'shipping_cost')

@admin.register(Governorate)
class GovernorateAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [AreaInline]

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'governorate', 'shipping_cost')
    list_filter = ('governorate',)
    search_fields = ('name',)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    # Already fixed: uses callable method
    list_display = ('user', 'street_address', 'area', 'get_governorate_name', 'is_default')
    
    # Already fixed: uses field traversal
    list_filter = ('is_default', 'area__governorate')
    search_fields = ('user__username', 'street_address', 'phone_number')

    def get_governorate_name(self, obj):
        """Displays the Governorate name by traversing Address -> Area -> Governorate."""
        return obj.area.governorate.name if obj.area and obj.area.governorate else 'N/A'
    get_governorate_name.short_description = 'Governorate'