from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone # Added import
from django.db.models import Q

# -----------------------
# Abstract Base Models
# -----------------------
class TimeStampedModel(models.Model):
    """Abstract base class that provides self-updating 'created_at' and 'updated_at' fields."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        
# -----------------------
# Custom User (No change needed)
# -----------------------
class CustomUser(AbstractUser):
    name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.email if self.email else self.username


# -----------------------
# Colors
# -----------------------
class Color(models.Model): 
    name = models.CharField(max_length=50, unique=True) 
    hex_code = models.CharField(max_length=7, unique=True) 

    def __str__(self):
        return self.name


# -----------------------
# Categories & Subcategories
# -----------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True) 
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    name = models.CharField(max_length=100) 
    image = models.ImageField(upload_to='subcategory_images/', blank=True, null=True)
    parent_category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories'
    )

    class Meta:
        unique_together = ('name', 'parent_category')

    def __str__(self):
        return f"{self.name} ({self.parent_category.name})"


# -----------------------
# Rooms & Styles
# -----------------------
class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='room_images/', blank=True, null=True)
    
    def __str__(self):
        return self.name

class Style(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='style_images/', blank=True, null=True)

    def __str__(self):
        return self.name


# -----------------------
# Products
# -----------------------
class Product(TimeStampedModel): # Applied TimeStampedModel for consistency
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=255, blank=True, null=True)
    
    dimensions = models.CharField(max_length=255, blank=True, null=True) 

    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_on_sale = models.BooleanField(default=False)
    sale_badge_image = models.ImageField(upload_to='sale_badges/', blank=True, null=True)
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        default=0.0
    )
    image = models.ImageField(upload_to='product_images/')
    
    colors = models.ManyToManyField(Color, related_name='products', blank=True)
    rooms = models.ManyToManyField(
        Room,
        related_name='products',
        blank=True
    )
    styles = models.ManyToManyField(
        Style,
        related_name='products',
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    # created_at is handled by TimeStampedModel

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products'
    )

    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )

    def get_current_price(self):
        """Returns the sale price if on sale, otherwise the original price."""
        if self.is_on_sale and self.sale_price is not None:
            return self.sale_price
        return self.original_price

    def save(self, *args, **kwargs):
        # Ensure subcategory belongs to category
        if self.subcategory and self.subcategory.parent_category != self.category:
            raise ValueError("Selected subcategory does not belong to the chosen category.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# NEW: Model for multiple product images (the gallery)
class ProductImage(TimeStampedModel): # Applied TimeStampedModel
    product = models.ForeignKey(
        Product,
        related_name='gallery_images',
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='product_gallery/')
    alt_text = models.CharField(max_length=255, blank=True) 
    # created_at is handled by TimeStampedModel
    
    color = models.ForeignKey(
        Color, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='product_images'
    )
    
    def __str__(self):
        return f"Image for {self.product.name}"


# NEW: Model for product reviews and ratings
class Review(TimeStampedModel): # Applied TimeStampedModel
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='reviews'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='reviews'
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, null=True) 
    # created_at is handled by TimeStampedModel
    
    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.product.name} by {self.user.username}"


# -----------------------
# Promotions
# -----------------------
class PromoBanner(models.Model):
    name = models.CharField(max_length=100, help_text="A name for internal reference")
    end_date = models.DateTimeField(help_text="The date and time when the promotion ends.")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# -----------------------
# Hero Slides
# -----------------------
class HeroSlide(models.Model):
    name = models.CharField(
        max_length=100,
        help_text="A name for internal reference (e.g., 'Summer Sale Banner')",
        default="Hero Slide"
    )
    title = models.CharField(max_length=200, blank=True, null=True)
    subtitle = models.CharField(max_length=300, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=255, blank=True, null=True)
    
    image = models.ImageField(upload_to='hero_slides/')
    button_text = models.CharField(max_length=50, blank=True, null=True)
    button_link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.name

# -----------------------
# New Model for Promotional Grids
# -----------------------
class PromoGridCategory(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True) # Retaining the 'name' field
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=255, blank=True, null=True)
    
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    image = models.ImageField(upload_to='promo_grid_images/')
    background_color = models.CharField(max_length=7, default='#000000', help_text="Hex code for the color overlay")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Determines the display order in the grid")

    class Meta:
        verbose_name_plural = "Promo Grid Categories"
        ordering = ['order']

    def __str__(self):
        return self.title

# -----------------------
# Coupon Model
# -----------------------
class Coupon(TimeStampedModel): # Applied TimeStampedModel
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Discount value as a percentage (e.g., 10 for 10%)"
    )
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

# -----------------------
# Shopping Cart
# -----------------------
class Cart(TimeStampedModel): # Applied TimeStampedModel
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    # created_at/updated_at are handled by TimeStampedModel

    def get_cart_total(self):
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.get_total_price()
        return total

    def __str__(self):
        return f"Cart for {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)

    def get_total_price(self):
        return self.quantity * self.product.get_current_price()

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.cart.user.username}'s Cart" 


# -----------------------
# Address & Location Models
# -----------------------
class Governorate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        verbose_name_plural = "Governorates"

    def __str__(self):
        return self.name

class Area(models.Model):
    name = models.CharField(max_length=100)
    governorate = models.ForeignKey(
        Governorate,
        on_delete=models.CASCADE,
        related_name='areas'
    )
    shipping_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )

    class Meta:
        unique_together = ('name', 'governorate')
        verbose_name_plural = "Areas"

    def __str__(self):
        return f"{self.name}, {self.governorate.name}"

class Address(TimeStampedModel): # Applied TimeStampedModel
    """
    Stores a user's saved shipping or billing addresses.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    street_address = models.CharField(max_length=255)
    apartment_details = models.CharField(max_length=255, blank=True, null=True)
    
    # 🎯 FIX APPLIED: Only link to Area, Governorate is accessed via Area
    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT, # Prevents deletion of a region if addresses rely on it
        related_name='addresses_used',
    )
    
    is_default = models.BooleanField(default=False)
    # created_at is handled by TimeStampedModel

    class Meta:
        verbose_name_plural = "Addresses"
        # Ensure only one address per user can be marked as default.
        # Using a conditional UniqueConstraint on is_default=True prevents
        # the previous incorrect behavior where unique_together(('user','is_default'))
        # disallowed multiple non-default addresses.
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_default=True),
                name='unique_default_address_per_user'
            )
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}'s address"

# -----------------------
# Order Models
# -----------------------
class Order(TimeStampedModel): # Applied TimeStampedModel
    STATUS_CHOICES = [
        ('PENDING', 'Pending Payment'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='orders')
    
    # Linked to the Address model (see notes above regarding best practice)
    shipping_address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='shipments'
    )
    
    cart_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    final_total = models.DecimalField(max_digits=10, decimal_places=2)

    coupon_code_used = models.CharField(max_length=50, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_status = models.CharField(max_length=50, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    # created_at/updated_at are handled by TimeStampedModel
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} - {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    
    product_name = models.CharField(max_length=200) 
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def get_total_price(self):
        return self.quantity * self.price_at_purchase

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"
# -----------------------
# User Favorites
# -----------------------
class Favorite(TimeStampedModel): # Applied TimeStampedModel
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    # added_at is handled by TimeStampedModel

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f'{self.user.username} favorites {self.product.name}'