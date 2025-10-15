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
    expiry_date = models.DateField(null=True, blank=True, help_text="Срок годности товара")
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
        """Get the first active offer for this item (include expired offers)"""
        from django.utils import timezone
        from django.db.models import Q
        
        return self.offers.filter(
            is_active=True,
            status='available',
            start_date__lte=timezone.now().date()
        ).first()
    
    def is_expired(self):
        """Check if item has expired"""
        from django.utils import timezone
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False
    
    def is_available(self):
        """Check if item is available (active and not expired)"""
        return self.is_active and not self.is_expired()

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


class SurpriseBox(models.Model):
    """
    Surprise Box model similar to Too Good To Go functionality
    Allows vendors to create mystery boxes with multiple items at discounted prices
    """
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'), 
        ('sold_out', 'Sold Out'),
        ('expired', 'Expired'),
    ]
    
    BOX_TYPE_CHOICES = [
        ('mixed', 'Смешанный бокс'),
        ('bakery', 'Хлебобулочные изделия'),
        ('meals', 'Готовые блюда'),
        ('groceries', 'Продукты'),
        ('desserts', 'Десерты'),
        ('beverages', 'Напитки'),
    ]
    
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='surprise_boxes')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='surprise_boxes')
    
    # Box information
    title = models.CharField(max_length=200, help_text="Например: 'Сюрприз бокс от Osh Markazi'")
    description = models.TextField(help_text="Описание того, что может быть в боксе")
    box_type = models.CharField(max_length=20, choices=BOX_TYPE_CHOICES, default='mixed')
    
    # Items in the box
    items = models.ManyToManyField(Item, through='SurpriseBoxItem', related_name='surprise_boxes')
    
    # Pricing
    original_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Общая стоимость товаров в боксе")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Цена продажи бокса")
    
    # Availability
    total_quantity = models.PositiveIntegerField(default=1, help_text="Сколько боксов доступно")
    reserved_quantity = models.PositiveIntegerField(default=0)
    sold_quantity = models.PositiveIntegerField(default=0)
    
    # Time constraints
    available_from = models.DateTimeField(help_text="С какого времени доступен бокс")
    available_until = models.DateTimeField(help_text="До какого времени доступен бокс")
    pickup_start = models.TimeField(blank=True, null=True, help_text="Время начала самовывоза")
    pickup_end = models.TimeField(blank=True, null=True, help_text="Время окончания самовывоза")
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Image for the box
    image = models.ImageField(upload_to='surprise_boxes/', null=True, blank=True)
    
    class Meta:
        verbose_name = "Сюрприз бокс"
        verbose_name_plural = "Сюрприз боксы"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.vendor.name}"
    
    @property
    def discount_percent(self):
        """Calculate discount percentage"""
        if self.original_value > 0:
            discount = (self.original_value - self.selling_price) / self.original_value * 100
            return round(discount, 1)
        return 0
    
    @property
    def available_quantity(self):
        """Get available quantity (not reserved or sold)"""
        return self.total_quantity - self.reserved_quantity - self.sold_quantity
    
    @property
    def is_available(self):
        """Check if box is currently available"""
        from django.utils import timezone
        now = timezone.now()
        
        return (
            self.is_active and
            self.status == 'available' and
            self.available_quantity > 0 and
            self.available_from <= now <= self.available_until
        )
    
    @property
    def is_pickup_time(self):
        """Check if it's currently pickup time"""
        from django.utils import timezone
        current_time = timezone.now().time()
        return self.pickup_start <= current_time <= self.pickup_end
    
    def get_absolute_url(self):
        return reverse('catalog:surprise_box_detail', args=[str(self.id)])


class SurpriseBoxItem(models.Model):
    """
    Through model for items in surprise boxes
    Allows specifying quantity and notes for each item
    """
    surprise_box = models.ForeignKey(SurpriseBox, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, help_text="Количество этого товара в боксе")
    notes = models.CharField(max_length=200, blank=True, help_text="Дополнительные заметки о товаре")
    
    class Meta:
        unique_together = ('surprise_box', 'item')
        verbose_name = "Товар в сюрприз боксе"
        verbose_name_plural = "Товары в сюрприз боксе"
    
    def __str__(self):
        return f"{self.item.title} x{self.quantity} в {self.surprise_box.title}"
