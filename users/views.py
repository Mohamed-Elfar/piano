from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError, APIException
from django.db.models import Prefetch
from django.db import transaction, IntegrityError
from django.http import JsonResponse

from django.contrib.auth import get_user_model
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from django.utils import timezone

from .filters import ProductFilter
from .serializers import (
    RegisterSerializer,
    MyTokenObtainPairSerializer,
    CategorySerializer,
    SubcategorySerializer,
    HeroSlideSerializer,
    PromoBannerSerializer,
    ProductDetailSerializer,
    ReviewSerializer,
    ProductSearchSerializer,
    RoomSerializer,
    StyleSerializer,
    PromoGridCategorySerializer,
    ColorSerializer,
    CartSerializer,
    CartItemSerializer, 
    FavoriteSerializer,
    UserProfileSerializer,
    # NEW IMPORTS
    GovernorateSerializer,
    AreaSerializer, 
    CheckoutSerializer,
    UserAddressSerializer, 
    OrderListSerializer, 
    OrderDetailSerializer, 
)
from .models import (
    Product,
    Review,
    Favorite,
    Category,
    Subcategory,
    HeroSlide,
    PromoBanner,
    Room,
    Style,
    PromoGridCategory,
    Cart,
    CartItem,
    Color,
    # NEW IMPORTS
    Governorate,
    Area,
    Coupon,
    Address, 
    Order, 
)

User = get_user_model()


def home(request):
    return HttpResponse("Welcome to the Piano project! Your API is ready.")


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# --- User Profile View ---
class UserProfileView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # 🌟 FIX FOR 500 ERROR: Removed the incorrect .get() call.
        # We start a queryset filtered by the authenticated user's ID (pk)
        # to ensure the prefetch_related optimization is applied correctly
        # and then retrieve the single object using .first().
        try:
            qs = User.objects.filter(pk=self.request.user.pk).prefetch_related(
                Prefetch('favorites', queryset=Favorite.objects.select_related('product')),
                Prefetch('order_set', queryset=Order.objects.order_by('-created_at')[:10])
            )
            # Use .get() so a missing user raises DoesNotExist (handled as 404)
            return qs.get()
        except User.DoesNotExist:
            raise NotFound("User not found")
        except Exception as exc:
            # Emit traceback to server logs for debugging and return a clean API error
            import traceback
            traceback.print_exc()
            raise APIException("Failed to retrieve user profile")

    def retrieve(self, request, *args, **kwargs):
        """
        Attempt to retrieve the full profile (with prefetch). If that fails
        due to related-object serialization or prefetch issues, fall back to
        returning a minimal serialized user object (no related favorites/orders)
        so the frontend can still display basic profile information while
        we diagnose the root cause.
        """
        try:
            obj = self.get_object()
            serializer = self.get_serializer(obj)
            return Response(serializer.data)
        except Exception as exc:
            # Log full traceback for debugging
            import traceback
            traceback.print_exc()
            # Try a minimal fallback: return the user without prefetching related data
            try:
                user = User.objects.get(pk=request.user.pk)
                # Build a lightweight serializer that only includes core fields
                fallback_data = {
                    'id': user.id,
                    'email': getattr(user, 'email', None),
                    'name': getattr(user, 'name', None),
                    'phone_number': getattr(user, 'phone_number', None),
                    'favorites': [],
                    'orders': [],
                }
                return Response(fallback_data, status=status.HTTP_200_OK)
            except Exception:
                # If even the fallback fails, return a clear API error
                return Response({'detail': 'Failed to retrieve user profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------
# NEW: User Address ViewSet
# -----------------------
class UserAddressViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for a user's saved shipping addresses.
    """
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Prefetch the related area and its governorate for read operations
        return Address.objects.filter(user=self.request.user).select_related('area__governorate').order_by('-is_default', '-created_at')

    def perform_create(self, serializer):
        # Safer creation flow to avoid UNIQUE constraint on (user,is_default):
        # 1. Create the address with is_default=False
        # 2. If the caller requested is_default=True, clear other defaults
        #    and set the created address to default within the same transaction.
        try:
            is_default = bool(serializer.validated_data.get('is_default', False))
        except Exception:
            is_default = False

        try:
            with transaction.atomic():
                # 1) Save the address with is_default=False to avoid duplicate default at insert
                created = serializer.save(user=self.request.user, is_default=False)

                # 2) If requested, flip the default flag in a separate update step
                if is_default:
                    # Clear any existing default addresses for this user
                    Address.objects.filter(user=self.request.user, is_default=True).exclude(pk=created.pk).update(is_default=False)
                    created.is_default = True
                    created.save()
        except IntegrityError as ie:
            import traceback
            traceback.print_exc()
            raise APIException('Failed to save address due to a database constraint. Try again.')
        except Exception:
            import traceback
            traceback.print_exc()
            raise APIException('Failed to save address. Contact support if the problem persists.')

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        try:
            address = self.get_queryset().get(pk=pk)
            
            # Clear default flag on all other addresses
            self.get_queryset().exclude(pk=pk).update(is_default=False)
            
            # Set this address as default
            address.is_default = True
            address.save()
            
            serializer = self.get_serializer(address)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Address.DoesNotExist:
            return Response({'error': 'Address not found.'}, status=status.HTTP_404_NOT_FOUND)

    def perform_update(self, serializer):
        """
        When updating an address, if it's being set as default, clear other defaults first.
        """
        try:
            is_default = serializer.validated_data.get('is_default', None)
        except Exception:
            is_default = None

        try:
            with transaction.atomic():
                # Save the update with is_default=False first to avoid uniqueness conflict
                if is_default is not None:
                    # Force is_default False for the save operation, then flip it if needed
                    updated = serializer.save(is_default=False)
                    if is_default:
                        Address.objects.filter(user=self.request.user, is_default=True).exclude(pk=updated.pk).update(is_default=False)
                        updated.is_default = True
                        updated.save()
                else:
                    # No change to is_default requested, just save normally
                    serializer.save()
        except IntegrityError:
            import traceback
            traceback.print_exc()
            raise APIException('Failed to update address due to a database constraint.')
        except Exception:
            import traceback
            traceback.print_exc()
            raise APIException('Failed to update address. Contact support if the problem persists.')


# -----------------------
# NEW: Order ViewSet
# -----------------------
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides list and detail views for a user's past orders.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Base queryset: only orders belonging to the authenticated user
        queryset = Order.objects.filter(user=self.request.user).order_by('-created_at')
        
        if self.action == 'retrieve':
            # Optimize detail view to pull all related data
            queryset = queryset.prefetch_related('items').select_related('shipping_address__area__governorate')
        
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return OrderListSerializer
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return super().get_serializer_class()


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self,):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class SubcategoryListView(generics.ListAPIView):
    serializer_class = SubcategorySerializer
    queryset = Subcategory.objects.all()
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(parent_category__id=category_id)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class HeroSlideViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HeroSlide.objects.filter(is_active=True).order_by('order')
    serializer_class = HeroSlideSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


# EDITED: Combine ProductViewSet and ProductDetailViewSet
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    search_fields = ['name', 'short_description', 'description']
    ordering_fields = ['original_price', 'rating', 'created_at']
    ordering = ['-created_at']
    filterset_class = ProductFilter
    
    def get_queryset(self):
        # Optimized to prefetch related data for detail view
        if self.action == 'retrieve':
            return Product.objects.prefetch_related(
                'gallery_images__color',
                'colors',
                'rooms',
                'styles',
                # Optimize to only fetch reviews and user data for reviews
                Prefetch('review_set', queryset=Review.objects.select_related('user').order_by('-created_at')), 
                Prefetch(
                    'favorite_set',
                    # Only fetch the favorite object if the current user has favorited it
                    queryset=Favorite.objects.filter(user=self.request.user) if self.request.user.is_authenticated else Favorite.objects.none()
                )
            ).select_related(
                'category',
                'subcategory'
            )
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductSearchSerializer
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        """
        Robust retrieve: try the full serialization path, but on unexpected
        exceptions return a minimal product representation so the frontend
        can still show basic product details while we collect tracebacks.
        """
        try:
            obj = self.get_object()
            serializer = self.get_serializer(obj)
            return Response(serializer.data)
        except Exception:
            import traceback
            traceback.print_exc()
            # Attempt a minimal fallback response
            try:
                pk = kwargs.get('pk') or request.parser_context.get('kwargs', {}).get('pk')
                product = Product.objects.filter(pk=pk).first()
                if not product:
                    return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

                fallback = {
                    'id': product.id,
                    'name': product.name,
                    'short_description': product.short_description,
                    'original_price': str(product.original_price),
                    'sale_price': str(product.sale_price) if product.sale_price is not None else None,
                    'is_on_sale': product.is_on_sale,
                    'image': request.build_absolute_uri(product.image.url) if product.image and hasattr(product.image, 'url') else None,
                }
                return Response(fallback, status=status.HTTP_200_OK)
            except Exception:
                traceback.print_exc()
                return Response({'detail': 'Failed to retrieve product'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoomViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Room.objects.all().order_by('name')
    serializer_class = RoomSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self,):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class StyleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Style.objects.all().order_by('name')
    serializer_class = StyleSerializer
    permission_classes = [AllowAny]


class ColorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Color.objects.all().order_by('name')
    serializer_class = ColorSerializer
    permission_classes = [AllowAny]


class PromoGridCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PromoGridCategory.objects.filter(is_active=True).order_by('order')
    serializer_class = PromoGridCategorySerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@api_view(['GET'])
def get_active_promo_banner(request):
    try:
        promo_banner = PromoBanner.objects.filter(is_active=True).order_by('-end_date').first()
        if promo_banner:
            serializer = PromoBannerSerializer(promo_banner, context={'request': request})
            return Response(serializer.data)
        else:
            return Response({"error": "No active promo banner found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def debug_filters(request):
    """Debug endpoint: echoes query params and shows how ProductFilter resolves them."""
    try:
        params = {k: request.GET.getlist(k) for k in request.GET.keys()}
        base_qs = Product.objects.filter(is_active=True)
        # apply ProductFilter (pass request so FilterSet can access getlist and other helpers)
        pf = ProductFilter(request.GET, queryset=base_qs, request=request)
        qs = pf.qs
        count = qs.count()
        sample = list(qs.values('id', 'name')[:5])
        return JsonResponse({'received': params, 'count': count, 'sample': sample})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
def product_suggestions(request):
    """Simple suggestions endpoint: returns product name suggestions based on a prefix."""
    q = request.GET.get('q', '')
    try:
        limit = int(request.GET.get('limit', 10))
    except Exception:
        limit = 10
    if not q:
        return Response({'suggestions': []})
    qs = Product.objects.filter(is_active=True, name__istartswith=q).order_by('name')[:limit]
    suggestions = [p.name for p in qs]
    return Response({'suggestions': suggestions})


# -----------------------
# Shopping Cart ViewSet
# -----------------------
class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        The base queryset for this viewset returns the single cart
        for the authenticated user. Optimized for serializer needs.
        """
        return Cart.objects.filter(user=self.request.user).select_related('coupon').prefetch_related(
            'items__product__colors',
            'items__product__category',
            'items__product__subcategory',
        )

    def list(self, request, *args, **kwargs):
        """
        A GET request to /api/cart/ (list route) will return the user's cart object.
        """
        try:
            cart = self.get_queryset().get()
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        except Cart.DoesNotExist:
            # If the cart doesn't exist, return an empty structure
            return Response({'items': [], 'cart_subtotal': '0.00', 'coupon_discount_amount': '0.00'}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        # Redirect retrieve to list for simpler URL routing
        return self.list(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        try:
            cart, _ = Cart.objects.get_or_create(user=self.request.user)
            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)
            
            try:
                # Ensure the product exists and is active
                product = Product.objects.get(pk=product_id, is_active=True)
            except Product.DoesNotExist:
                return Response({"error": "Product not found or inactive."}, status=status.HTTP_404_NOT_FOUND)

            # NOTE: Logic here handles the creation/update
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )

            if not created:
                # If item already exists, increase quantity
                cart_item.quantity += int(quantity)
                cart_item.save()
            
            # Return the updated cart
            # Re-fetch cart with prefetch for clean serialization
            updated_cart = self.get_queryset().get(user=self.request.user)
            serializer = self.get_serializer(updated_cart)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            # Catch potential non-integer quantity errors etc.
            return Response({"error": f"Failed to add item: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

# -----------------------
# NEW: Apply Coupon View
# -----------------------
class ApplyCouponView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer
    
    def get_object(self):
        """
        Returns the cart object for the authenticated user, or raises NotFound if it doesn't exist.
        Includes optimization (prefetching) for the serializer.
        """
        try:
            # Use the optimized queryset logic from CartViewSet
            # CRITICAL: Since CartViewSet is a class, we need to instantiate it or call its methods
            # in a way that provides self.request.
            cart_qs = Cart.objects.filter(user=self.request.user).select_related('coupon').prefetch_related(
                'items__product__colors',
                'items__product__category',
                'items__product__subcategory',
            )
            cart = cart_qs.get()
            return cart
        except Cart.DoesNotExist:
            raise NotFound("User does not have an active cart.")


    def put(self, request, *args, **kwargs):
        # Get the cart instance (already optimized via get_object)
        cart = self.get_object() 
        coupon_code = request.data.get('coupon_code')
        
        # --- Logic to remove a coupon ---
        if not coupon_code:
            cart.coupon = None
            cart.save()
            # Must re-fetch for serialization to get the updated values, but we can reuse the optimized cart object
            serializer = self.get_serializer(cart) 
            return Response(serializer.data, status=status.HTTP_200_OK)

        # --- Logic to apply a new coupon ---
        try:
            coupon = Coupon.objects.get(
                code__iexact=coupon_code,
                is_active=True,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now()
            )
        except Coupon.DoesNotExist:
            raise ValidationError({'coupon_code': 'Invalid or expired coupon code.'})

        cart.coupon = coupon
        cart.save()
        
        # Return the updated cart with the new coupon applied
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


# -----------------------
# NEW: Shopping Cart Item ViewSet
# -----------------------
class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Only allow users to see and modify their own cart items.
        """
        return CartItem.objects.filter(cart__user=self.request.user).select_related('product')
    
    def perform_create(self, serializer):
        # Ensure the item is created in the user's cart
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        # Note: The serializer's product_id field (source='product') handles the FK to Product
        serializer.save(cart=cart)
    

# -----------------------
# User Favorites ViewSet
# -----------------------
# In your views.py
class FavoriteViewSet(viewsets.ModelViewSet):
    # ... (omitted code) ...

    @action(detail=False, methods=['post'])
    def add_or_remove(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            # CORRECT: Returns a clean 400 if product_id is missing.
            return Response({'error': 'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            # CORRECT: Returns a clean 404 if product is not found.
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Correctly implements the toggle logic
        favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)

        if not created:
            favorite.delete()
            # CORRECT: Returns 200 OK for removal.
            return Response({'message': 'Product removed from favorites', 'is_favorited': False}, status=status.HTTP_200_OK)

        # CORRECT: Returns 201 CREATED for addition.
        serializer = self.get_serializer(favorite)
        return Response({'message': 'Product added to favorites', 'is_favorited': True, 'favorite': serializer.data}, status=status.HTTP_201_CREATED)
    """
    A viewset for a user's favorite products.
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Optimized to prefetch the product data
        return Favorite.objects.filter(user=self.request.user).prefetch_related('product')

    @action(detail=False, methods=['post'])
    def add_or_remove(self, request):
        # Robust favorite toggle handler with detailed error handling/logging.
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Ensure product_id is an integer-like value
            product_pk = int(product_id)
        except (ValueError, TypeError):
            return Response({'error': 'Product ID must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)

            if not created:
                favorite.delete()
                return Response({'message': 'Product removed from favorites', 'is_favorited': False}, status=status.HTTP_200_OK)

            # Return serialized favorite (ensure serializer has request context)
            serializer = FavoriteSerializer(favorite, context={'request': request})
            return Response({'message': 'Product added to favorites', 'is_favorited': True, 'favorite': serializer.data}, status=status.HTTP_201_CREATED)

        except Exception as exc:
            # Catch database or unexpected errors and return informative response
            import traceback
            tb = traceback.format_exc()
            # Log traceback to server console for debugging
            print('Error in favorites.add_or_remove:', str(exc))
            print(tb)
            return Response({'error': 'Internal server error toggling favorite', 'details': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        # Ensure only the user's favorite is deleted using the primary key
        try:
            favorite = self.get_queryset().get(pk=self.kwargs['pk'])
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            return Response({"error": "Favorite not found."}, status=status.HTTP_404_NOT_FOUND)


# -----------------------
# NEW: Product Review ViewSet
# -----------------------
class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    
    def get_queryset(self):
        # Filter reviews based on the URL's product_pk (e.g., /products/1/reviews/)
        product_pk = self.kwargs.get('product_pk')
        if product_pk:
            # Select related user for the review serializer
            return Review.objects.filter(product_id=product_pk).select_related('user').order_by('-created_at')
        return Review.objects.none()
    
    def get_permissions(self):
        # Only authenticated users can create/update/delete reviews
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        # All users can view reviews
        return [AllowAny()]
    
    # Ensure the user only updates/deletes their own review
    def get_object(self):
        # Use get_queryset to ensure the review belongs to the correct product
        # and then filter by the primary key from the URL kwargs.
        obj = self.get_queryset().get(pk=self.kwargs['pk'])
        
        if self.action in ['update', 'partial_update', 'destroy'] and obj.user != self.request.user:
            # Raise a 403 or 404 to deny access/hide existence
            raise NotFound('Review not found or you do not have permission.')
        
        return obj

    def perform_create(self, serializer):
        product_pk = self.kwargs.get('product_pk')
        try:
            product = Product.objects.get(pk=product_pk)
            # Check for existing review explicitly before saving
            if Review.objects.filter(user=self.request.user, product=product).exists():
                raise ValidationError({"non_field_errors": ["You have already reviewed this product."]})

            serializer.save(user=self.request.user, product=product)
        except Product.DoesNotExist:
            raise NotFound("Product not found.")
        except Exception as e:
            # If a unique constraint error somehow still occurs, raise a generic error
            if 'unique constraint' in str(e).lower():
                raise ValidationError({"non_field_errors": ["You have already reviewed this product."]})
            raise e

# -----------------------
# NEW: Location ViewSet (Governorates & Areas)
# -----------------------
class GovernorateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a list of Governorates and their associated Areas and shipping costs.
    """
    # CRITICAL: Prefetch the related 'areas' for nested serialization
    queryset = Governorate.objects.all().prefetch_related('areas') 
    serializer_class = GovernorateSerializer
    permission_classes = [AllowAny]

class AreaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a list of all Areas, primarily used for populating dropdowns 
    in the shipping address form based on the selected governorate.
    """
    # CRITICAL: Select related governorate to display shipping info
    queryset = Area.objects.all().select_related('governorate')
    serializer_class = AreaSerializer 
    permission_classes = [AllowAny] 
    
# -----------------------
# NEW: Final Checkout View
# -----------------------
class CheckoutView(generics.CreateAPIView):
    """
    Handles the final POST request to convert the user's cart into an Order.
    """
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # `perform_create` calls serializer.create(), which executes the atomic logic
        order = self.perform_create(serializer)
        
        # Using OrderDetailSerializer to return the full order object for immediate confirmation
        order_serializer = OrderDetailSerializer(order, context={'request': request})
        return Response(
            order_serializer.data, 
            status=status.HTTP_201_CREATED
        )

    def perform_create(self, serializer):
        # This calls the complex, atomic logic defined in CheckoutSerializer's create()
        return serializer.save()