from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers 
from .views import (
    MyTokenObtainPairView,
    RegisterView,
    CategoryViewSet,
    HeroSlideViewSet,
    ProductViewSet,
    ReviewViewSet, 
    get_active_promo_banner,
    SubcategoryListView,
    RoomViewSet,
    StyleViewSet,
    ColorViewSet,
    PromoGridCategoryViewSet,
    CartViewSet,
    CartItemViewSet,
    FavoriteViewSet,
    UserProfileView,
    debug_filters,
    product_suggestions,
    # NEW IMPORTS FOR CHECKOUT & USER
    GovernorateViewSet,
    # 🌟 NEW: AreaViewSet was the missing piece 🌟
    AreaViewSet, 
    ApplyCouponView,
    CheckoutView,
    UserAddressViewSet, 
    OrderViewSet, 
)

# ----------------------------
# 1. Main Default Router
# ----------------------------
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'hero-slides', HeroSlideViewSet, basename='hero-slides')
router.register(r'products', ProductViewSet, basename='products')
router.register(r'rooms', RoomViewSet, basename='rooms')
router.register(r'styles', StyleViewSet, basename='styles')
router.register(r'colors', ColorViewSet, basename='colors')
router.register(r'promo-grid-categories', PromoGridCategoryViewSet, basename='promo-grid-categories')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'favorites', FavoriteViewSet, basename='favorites')
router.register(r'governorates', GovernorateViewSet, basename='governorates')
router.register(r'areas', AreaViewSet, basename='areas') # 🌟 FIX: Added the missing AreaViewSet registration
router.register(r'cart-items', CartItemViewSet, basename='cart-items')

# ----------------------------
# 2. User-Specific Routers
# ----------------------------
# NEW: Router for user addresses
router.register(r'user/addresses', UserAddressViewSet, basename='user-addresses')

# NEW: Router for user orders
router.register(r'user/orders', OrderViewSet, basename='user-orders')


# ----------------------------
# 3. Nested Router for Reviews
# ----------------------------
products_router = routers.NestedSimpleRouter(router, r'products', lookup='product')
products_router.register(r'reviews', ReviewViewSet, basename='product-reviews')


# ----------------------------
# 4. URL Patterns (Combining Routers and Manual Paths)
# ----------------------------
urlpatterns = [
    # Include all URLs from the main router.
    path('', include(router.urls)),
    
    # Include all URLs from the nested router (for /products/{pk}/reviews/).
    path('', include(products_router.urls)),

    # --- Authentication endpoints ---
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('register/', RegisterView.as_view(), name='auth_register'),

    # --- User Profile & Suggestions ---
    path('product-suggestions/', product_suggestions, name='product-suggestions'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),

    # --- Cart & Checkout Endpoints ---
    path('cart/apply-coupon/', ApplyCouponView.as_view(), name='apply-coupon'),
    path('checkout/', CheckoutView.as_view(), name='checkout-order'),

    # --- Miscellaneous Endpoints ---
    path('subcategories/', SubcategoryListView.as_view(), name='subcategory-list'),
    path('promo-banner/', get_active_promo_banner, name='active-promo-banner'),
    path('debug/filters/', debug_filters, name='debug-filters'),
]