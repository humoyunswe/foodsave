from django.db import models
from django.contrib.auth import get_user_model

from catalog.models import Offer
from vendors.models import Branch

User = get_user_model()

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    DELIVERY_CHOICES = [
        ('delivery', 'Delivery'),
        ('pickup', 'Pickup'),
    ]
    
    PAYMENT_CHOICES = [
        ('card', 'Card'),
        ('cash', 'Cash'),
        ('apple_pay', 'Apple Pay'),
        ('google_pay', 'Google Pay'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_CHOICES)
    delivery_address = models.TextField(blank=True)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.order_number}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.offer.item.title} x{self.quantity}"

class CartItem(models.Model):
    """Модель для хранения товаров в корзине пользователя"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)  # Для анонимных пользователей
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'offer'], ['session_key', 'offer']]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.offer.item.title} x{self.quantity}"
    
    @property
    def total_price(self):
        return self.offer.current_price * self.quantity
    
    @property
    def savings(self):
        if self.offer.original_price > self.offer.current_price:
            return (self.offer.original_price - self.offer.current_price) * self.quantity
        return 0