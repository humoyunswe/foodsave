from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.urls import reverse_lazy
from .models import Order, OrderItem, CartItem
from .forms import CheckoutForm, OrderSearchForm
from catalog.models import Offer
import uuid
import json


class CartView(TemplateView):
    template_name = 'booking/cart.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем товары из корзины
        if self.request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=self.request.user).select_related(
                'offer__item__vendor', 'offer__item__category'
            ).prefetch_related('offer__item__images')
        else:
            session_key = self.request.session.session_key
            if session_key:
                cart_items = CartItem.objects.filter(session_key=session_key).select_related(
                    'offer__item__vendor', 'offer__item__category'
                ).prefetch_related('offer__item__images')
            else:
                cart_items = CartItem.objects.none()
        
        # Вычисляем итоги
        total_amount = sum(item.total_price for item in cart_items)
        total_savings = sum(item.savings for item in cart_items)
        total_items = sum(item.quantity for item in cart_items)
        original_total = total_amount + total_savings if (total_amount or total_savings) else 0
        savings_percent = round((total_savings / original_total) * 100, 1) if original_total > 0 else 0
        
        # Группируем по продавцам для удобства отображения
        vendors_items = {}
        for item in cart_items:
            vendor = item.offer.item.vendor
            if vendor not in vendors_items:
                vendors_items[vendor] = []
            vendors_items[vendor].append(item)
        
        context.update({
            'cart_items': cart_items,
            'vendors_items': vendors_items,
            'total_amount': total_amount,
            'total_savings': total_savings,
            'total_items': total_items,
            'savings_percent': savings_percent,
            'delivery_fee': 5000,  # 5000 сум фиксированная стоимость доставки
            'final_total': total_amount + 5000,
        })
        
        return context


class CheckoutView(LoginRequiredMixin, CreateView):
    model = Order
    form_class = CheckoutForm
    template_name = 'booking/checkout.html'
    success_url = reverse_lazy('booking:order_list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate total amount (this would normally come from cart)
        form.instance.total_amount = 0
        form.instance.delivery_fee = 5.00  # Fixed delivery fee for now
        
        with transaction.atomic():
            response = super().form_valid(form)
            
            # Here you would create OrderItems from cart data
            # For now, we'll create a placeholder
            
            messages.success(self.request, f'Заказ {self.object.order_number} успешно создан!')
            return response


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'booking/order_detail.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__offer__item')


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'booking/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


@csrf_exempt
@require_http_methods(["POST"])
def add_to_cart(request):
    """API для добавления товара в корзину"""
    try:
        data = json.loads(request.body)
        offer_id = data.get('offer_id')
        quantity = int(data.get('quantity', 1))
        
        if not offer_id:
            return JsonResponse({'success': False, 'message': 'Не указан ID предложения'})
        
        # Получаем предложение
        try:
            offer = Offer.objects.select_related('item', 'item__vendor').get(id=offer_id, is_active=True)
        except Offer.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Предложение не найдено'})
        
        # Проверяем доступность
        if offer.quantity_remaining is not None and offer.quantity_remaining < quantity:
            return JsonResponse({
                'success': False, 
                'message': f'Недостаточно товара. Доступно: {offer.quantity_remaining} шт.'
            })
        
        # Определяем пользователя или сессию
        if request.user.is_authenticated:
            cart_item, created = CartItem.objects.get_or_create(
                user=request.user,
                offer=offer,
                defaults={'quantity': quantity}
            )
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            
            cart_item, created = CartItem.objects.get_or_create(
                session_key=session_key,
                offer=offer,
                defaults={'quantity': quantity}
            )
        
        if not created:
            # Увеличиваем количество
            new_quantity = cart_item.quantity + quantity
            if offer.quantity_remaining is not None and offer.quantity_remaining < new_quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Недостаточно товара. В корзине: {cart_item.quantity}, доступно: {offer.quantity_remaining}'
                })
            cart_item.quantity = new_quantity
            cart_item.save()
        
        # Получаем общее количество товаров в корзине
        if request.user.is_authenticated:
            cart_count = CartItem.objects.filter(user=request.user).count()
        else:
            cart_count = CartItem.objects.filter(session_key=session_key).count()
        
        return JsonResponse({
            'success': True,
            'message': f'{offer.item.title} добавлен в корзину!',
            'cart_count': cart_count,
            'item_quantity': cart_item.quantity,
            'total_price': float(cart_item.total_price)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Неверный формат данных'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка сервера: {str(e)}'})

@csrf_exempt
@require_http_methods(["POST"])
def update_cart_item(request):
    """API для обновления количества товара в корзине"""
    try:
        data = json.loads(request.body)
        cart_item_id = data.get('cart_item_id')
        quantity = int(data.get('quantity', 1))
        
        if not cart_item_id:
            return JsonResponse({'success': False, 'message': 'Не указан ID товара в корзине'})
        
        if quantity < 1:
            return JsonResponse({'success': False, 'message': 'Количество должно быть больше 0'})
        
        # Получаем товар в корзине
        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartItem, id=cart_item_id, user=request.user)
        else:
            session_key = request.session.session_key
            cart_item = get_object_or_404(CartItem, id=cart_item_id, session_key=session_key)
        
        # Проверяем доступность
        if cart_item.offer.quantity_remaining is not None and cart_item.offer.quantity_remaining < quantity:
            return JsonResponse({
                'success': False,
                'message': f'Недостаточно товара. Доступно: {cart_item.offer.quantity_remaining} шт.'
            })
        
        cart_item.quantity = quantity
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Количество обновлено',
            'item_quantity': cart_item.quantity,
            'total_price': float(cart_item.total_price)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Неверный формат данных'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка сервера: {str(e)}'})

@csrf_exempt
@require_http_methods(["POST"])
def remove_from_cart(request):
    """API для удаления товара из корзины"""
    try:
        data = json.loads(request.body)
        cart_item_id = data.get('cart_item_id')
        
        if not cart_item_id:
            return JsonResponse({'success': False, 'message': 'Не указан ID товара в корзине'})
        
        # Получаем и удаляем товар из корзины
        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartItem, id=cart_item_id, user=request.user)
            cart_count = CartItem.objects.filter(user=request.user).count() - 1
        else:
            session_key = request.session.session_key
            cart_item = get_object_or_404(CartItem, id=cart_item_id, session_key=session_key)
            cart_count = CartItem.objects.filter(session_key=session_key).count() - 1
        
        item_title = cart_item.offer.item.title
        cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{item_title} удален из корзины',
            'cart_count': cart_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Неверный формат данных'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка сервера: {str(e)}'})

@require_http_methods(["GET"])
def get_cart_count(request):
    """API для получения количества товаров в корзине"""
    try:
        if request.user.is_authenticated:
            cart_count = CartItem.objects.filter(user=request.user).count()
        else:
            session_key = request.session.session_key
            if session_key:
                cart_count = CartItem.objects.filter(session_key=session_key).count()
            else:
                cart_count = 0
        
        return JsonResponse({
            'success': True,
            'cart_count': cart_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка сервера: {str(e)}'})
