from django.db import models

# Create your models here.
from vendors.models import Vendor, Branch
from users.models import User
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.ImageField(upload_to='category_icons/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Item(models.Model):
    UNIT_CHOICES = [
        ('шт', 'Штуки'),
        ('кг', 'Килограммы'),
        ('порция', 'Порция'),
        ('литр', 'Литр'),
        ('г', 'Граммы'),
        ('мл', 'Миллилитры'),
        ('другое', 'Другое'),
    ]
    
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='items')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='items')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='шт')
    custom_unit = models.CharField(max_length=50, blank=True, help_text="Укажите единицу измерения, если выбрали 'Другое'")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    def get_unit_display_custom(self):
        """Return custom unit if 'другое' is selected, otherwise return standard unit display"""
        if self.unit == 'другое' and self.custom_unit:
            return self.custom_unit
        return self.get_unit_display()

    def get_active_offer(self):
        """Get the first active offer for this item"""
        from django.utils import timezone
        return self.offers.filter(
            is_active=True,
            status='available',
            start_date__lte=timezone.now().date()
        ).first()

    @property
    def name(self):
        """Alias for title to match template expectations"""
        return self.title

    def get_absolute_url(self):
        return reverse('catalog:item_detail', args=[str(self.id)])

class ItemImage(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='item_images/')
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

class Offer(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold_out', 'Sold Out'),
        ('expired', 'Expired'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='offers')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='offers')
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.FloatField(default=0.0)
    quantity = models.PositiveIntegerField(default=0)  # 0 means unlimited
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # null means no end date
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def current_price(self):
        """Calculate current price with discount"""
        if self.discount_percent > 0:
            from decimal import Decimal
            discount_decimal = Decimal(str(self.discount_percent))
            return self.original_price * (1 - discount_decimal / 100)
        return self.original_price

    @property
    def discounted_price(self):
        """Alias for current_price to match template expectations"""
        return self.current_price

    def __str__(self):
        return f"{self.item.title} - {self.discount_percent}% off"

    @property
    def is_expired(self):
        from django.utils import timezone
        if self.end_date:
            return timezone.now().date() > self.end_date
        return False
