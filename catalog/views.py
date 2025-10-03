from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from django.contrib import messages
from django.core.paginator import Paginator
import math
from .models import Item, Category, Offer, SurpriseBox
from .forms import CategoryForm, UnitForm
from vendors.models import Vendor, Branch
from django.utils import timezone
from django.utils.text import slugify
import json


from vendors.models import Branch, Vendor

def catalog_view(request):
    queryset = Item.objects.filter(is_active=True).select_related('vendor', 'category', 'branch').prefetch_related(
        'images',
        'offers__branch'
    )
    
    # Filter by categories (checkbox filter)
    categories = request.GET.getlist('categories')
    if categories:
        queryset = queryset.filter(category__id__in=categories)
    
    # Filter by vendors (checkbox filter)
    vendors_filter = request.GET.getlist('vendors')
    if vendors_filter:
        queryset = queryset.filter(vendor__id__in=vendors_filter)
    
    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and max_price:
        try:
            min_price = float(min_price)
            max_price = float(max_price)
            queryset = queryset.filter(
                offers__discounted_price__gte=min_price, 
                offers__discounted_price__lte=max_price,
                offers__is_active=True, 
                offers__status='available'
            )
        except ValueError:
            pass
    
    # Filter by distance (if user location is provided)
    distance_filter = request.GET.get('distance')
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    if distance_filter and user_lat and user_lng:
        try:
            max_distance = float(distance_filter)
            user_lat = float(user_lat)
            user_lng = float(user_lng)
            # This would need a more complex implementation with spatial queries
            # For now, we'll just pass the parameters to the template
        except ValueError:
            pass
    
    # Filter by vendor type (products vs dishes)
    vendor_type = request.GET.get('type')
    if vendor_type == 'products':
        queryset = queryset.filter(vendor__type='store')
    elif vendor_type == 'dishes':
        queryset = queryset.filter(vendor__type__in=['restaurant', 'cafe'])
    
    # Filter by discount percentage
    discount_filter = request.GET.get('discount')
    if discount_filter:
        try:
            min_discount = int(discount_filter)
            queryset = queryset.filter(offers__discount_percent__gte=min_discount, offers__is_active=True, offers__status='available')
        except ValueError:
            pass
    
    # Sorting
    sort_by = request.GET.get('sort')
    if sort_by == 'price_asc':
        queryset = queryset.order_by('offers__discounted_price')
    elif sort_by == 'price_desc':
        queryset = queryset.order_by('-offers__discounted_price')
    elif sort_by == 'discount':
        queryset = queryset.order_by('-offers__discount_percent')
    elif sort_by == 'rating':
        queryset = queryset.order_by('-vendor__rating')
    elif sort_by == 'distance':
        # Distance sorting would need spatial queries implementation
        queryset = queryset.order_by('-created_at')
    else:
        # Default sorting: items with active offers first, then by creation date
        queryset = queryset.order_by('-offers__is_active', '-created_at')
    
    # Remove duplicates that might occur due to multiple offers per item
    queryset = queryset.distinct()
    
    # Pagination
    paginator = Paginator(queryset, 12)
    page_number = request.GET.get('page')
    items = paginator.get_page(page_number)
    
    # Get all vendors for the filter
    vendors = Vendor.objects.filter(is_active=True).order_by('name')
    
    # Get available Surprise Boxes
    surprise_boxes = SurpriseBox.objects.filter(
        is_active=True,
        status='available',
        available_from__lte=timezone.now(),
        available_until__gte=timezone.now()
    ).select_related('vendor', 'branch').prefetch_related('items')[:6]  # Показываем только 6 боксов
    
    # Context data
    context = {
        'items': items,
        'surprise_boxes': surprise_boxes,
        'categories': Category.objects.filter(is_active=True),
        'vendors': vendors,
        'current_type': request.GET.get('type', ''),
        'is_paginated': items.has_other_pages(),
        'page_obj': items,
        'selected_categories': categories,
        'selected_vendors': vendors_filter,
        'min_price': min_price,
        'max_price': max_price,
        'selected_distance': distance_filter,
        'user_lat': user_lat,
        'user_lng': user_lng,
    }
    
    return render(request, 'catalog/catalog.html', context)


class CategoryView(ListView):
    model = Item
    template_name = 'catalog/category.html'
    context_object_name = 'items'
    paginate_by = 12
    
    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs['category_slug'])
        return Item.objects.filter(category=self.category, is_active=True).select_related('vendor')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = Category.objects.filter(is_active=True)
        return context


def item_detail_view(request, pk):
    """Function-based view for item detail page"""
    # Get the item with related data
    item = get_object_or_404(
        Item.objects.filter(is_active=True).select_related('vendor', 'category', 'branch'),
        pk=pk
    )
    
    # Get available offers for this item with quantity available
    offers = item.offers.filter(
        status='available', 
        is_active=True
    ).select_related('branch').order_by('-discount_percent')
    
    # Add quantity_available property to each offer
    for offer in offers:
        offer.quantity_available = offer.quantity if offer.quantity > 0 else "Неограничено"
    
    # Get item images ordered by their order field
    images = item.images.all().order_by('order')
    
    # Get branch information
    branch = item.branch
    
    context = {
        'item': item,
        'offers': offers,
        'images': images,
        'branch': branch,
        'phone': branch.phone if branch else None,
        'address': branch.address if branch else None,
        'opening_hours': branch.get_today_hours() if branch else None,
        'is_open': branch.is_open_now() if branch else False,
    }
    
    return render(request, 'catalog/item_detail.html', context)


class SearchView(ListView):
    model = Item
    template_name = 'catalog/search.html'
    context_object_name = 'items'
    paginate_by = 12
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Item.objects.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query) |
                Q(vendor__name__icontains=query),
                is_active=True
            ).select_related('vendor', 'category')
        return Item.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


class MapView(ListView):
    model = Item
    template_name = 'catalog/map_simple.html'
    context_object_name = 'nearby_items'
    
    def get_queryset(self):
        user_lat = float(self.request.GET.get('lat', 0))
        user_lng = float(self.request.GET.get('lng', 0))
        
        if not user_lat or not user_lng:
            return Item.objects.none()
        
        # Get all active items with their branches
        items = Item.objects.filter(is_active=True).select_related('vendor', 'branch', 'category')
        
        # Calculate distances and sort by proximity
        items_with_distance = []
        for item in items:
            if item.branch and item.branch.latitude and item.branch.longitude:
                distance = calculate_distance(
                    user_lat, user_lng,
                    float(item.branch.latitude), 
                    float(item.branch.longitude)
                )
                items_with_distance.append((item, distance))
        
        # Sort by distance and return closest 20 items
        items_with_distance.sort(key=lambda x: x[1])
        return [item for item, distance in items_with_distance[:20]]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_lat = self.request.GET.get('lat')
        user_lng = self.request.GET.get('lng')
        
        context['user_lat'] = user_lat
        context['user_lng'] = user_lng
        
        # Prepare items with distances for the map
        items_data = []
        for item in context['nearby_items']:
            if item.branch and item.branch.latitude and item.branch.longitude:
                distance = calculate_distance(
                    float(user_lat), float(user_lng),
                    float(item.branch.latitude), 
                    float(item.branch.longitude)
                )
                items_data.append({
                    'item': item,
                    'distance': round(distance, 2),
                    'lat': float(item.branch.latitude),
                    'lng': float(item.branch.longitude)
                })
        
        context['items_data'] = items_data
        return context


def get_recommendations(request):
    """API endpoint для получения рекомендаций товаров"""
    from django.db.models import Count, Avg
    from datetime import date
    import random
    
    try:
        # Получаем активные предложения с товарами
        offers = Offer.objects.filter(
            is_active=True,
            status='available',
            item__is_active=True,
            item__vendor__is_active=True,
            start_date__lte=date.today()
        ).select_related(
            'item', 
            'item__vendor', 
            'item__category'
        ).prefetch_related('item__images')
        
        # Исключаем товары, которые уже в корзине
        cart_items = getattr(request, 'session', {}).get('cart', [])
        cart_item_ids = [item.get('item_id') for item in cart_items if item.get('item_id')]
        if cart_item_ids:
            offers = offers.exclude(item_id__in=cart_item_ids)
        
        # Алгоритм рекомендаций
        recommendations = []
        
        # 1. Товары с высокой скидкой
        high_discount_items = offers.filter(
            discount_percent__gte=20
        ).order_by('-discount_percent')[:10]
        
        # 2. Случайные товары для разнообразия
        random_items = list(offers.order_by('?')[:10])
        
        # Объединяем и убираем дубликаты
        all_offers = list(high_discount_items) + list(random_items)
        seen_items = set()
        unique_offers = []
        
        for offer in all_offers:
            if offer.item_id not in seen_items and len(unique_offers) < 12:
                unique_offers.append(offer)
                seen_items.add(offer.item_id)
        
        # Формируем ответ
        recommendations_data = []
        for offer in unique_offers:
            item = offer.item
            try:
                primary_image = item.images.filter(is_primary=True).first()
                image_url = primary_image.image.url if primary_image else ''
            except:
                image_url = ''
            
            # Определяем тип бейджа
            badge_type = 'discount'
            badge_text = f'-{int(offer.discount_percent)}%'
            
            if offer.discount_percent >= 50:
                badge_type = 'hot'
                badge_text = 'ГОРЯЧЕЕ'
            
            recommendations_data.append({
                'id': item.id,
                'title': item.title or 'Без названия',
                'vendor_name': item.vendor.name if item.vendor else 'Неизвестный продавец',
                'original_price': float(offer.original_price),
                'current_price': float(offer.current_price),
                'discount_percent': int(offer.discount_percent),
                'image_url': image_url,
                'badge_type': badge_type,
                'badge_text': badge_text,
                'unit': dict(item.UNIT_CHOICES).get(item.unit, item.unit) if hasattr(item, 'UNIT_CHOICES') else 'шт',
                'category': item.category.name if item.category else '',
                'description': (item.description[:100] + '...') if item.description and len(item.description) > 100 else (item.description or '')
            })
        
        # Если нет рекомендаций, возвращаем пустой массив
        if not recommendations_data:
            return JsonResponse({
                'success': True,
                'recommendations': [],
                'message': 'Нет доступных рекомендаций'
            })
        
        return JsonResponse({
            'success': True,
            'recommendations': recommendations_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_quick_sets(request):
    """API endpoint для получения быстрых наборов товаров"""
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        # Получаем активные предложения
        offers = Offer.objects.filter(
            is_active=True,
            status='available',
            item__is_active=True,
            item__vendor__is_active=True,
            start_date__lte=timezone.now().date()
        ).select_related(
            'item', 
            'item__vendor', 
            'item__category'
        ).prefetch_related('item__images')
        
        # Создаем быстрые наборы на основе категорий
        quick_sets = []
        
        # Набор 1: Молочные продукты
        dairy_items = offers.filter(
            item__category__name__icontains='молоко'
        ).order_by('-discount_percent')[:3]
        
        if dairy_items.exists():
            quick_sets.append({
                'id': 'dairy',
                'name': '🥛 Молочные продукты',
                'description': 'Молоко, сыр, йогурт',
                'items': [{
                    'id': offer.item.id,
                    'title': offer.item.title,
                    'vendor_name': offer.item.vendor.name,
                    'current_price': float(offer.current_price),
                    'original_price': float(offer.original_price),
                    'discount_percent': int(offer.discount_percent),
                    'image_url': offer.item.images.filter(is_primary=True).first().image.url if offer.item.images.filter(is_primary=True).first() else '/static/images/placeholder.jpg'
                } for offer in dairy_items]
            })
        
        # Набор 2: Хлебобулочные изделия
        bakery_items = offers.filter(
            item__category__name__icontains='хлеб'
        ).order_by('-discount_percent')[:3]
        
        if bakery_items.exists():
            quick_sets.append({
                'id': 'bakery',
                'name': '🍞 Хлебобулочные',
                'description': 'Хлеб, булочки, выпечка',
                'items': [{
                    'id': offer.item.id,
                    'title': offer.item.title,
                    'vendor_name': offer.item.vendor.name,
                    'current_price': float(offer.current_price),
                    'original_price': float(offer.original_price),
                    'discount_percent': int(offer.discount_percent),
                    'image_url': offer.item.images.filter(is_primary=True).first().image.url if offer.item.images.filter(is_primary=True).first() else '/static/images/placeholder.jpg'
                } for offer in bakery_items]
            })
        
        # Набор 3: Популярные товары (по скидкам)
        popular_items = offers.order_by('-discount_percent')[:4]
        
        if popular_items.exists():
            quick_sets.append({
                'id': 'popular',
                'name': '🔥 Горячие предложения',
                'description': 'Самые выгодные скидки',
                'items': [{
                    'id': offer.item.id,
                    'title': offer.item.title,
                    'vendor_name': offer.item.vendor.name,
                    'current_price': float(offer.current_price),
                    'original_price': float(offer.original_price),
                    'discount_percent': int(offer.discount_percent),
                    'image_url': offer.item.images.filter(is_primary=True).first().image.url if offer.item.images.filter(is_primary=True).first() else '/static/images/placeholder.jpg'
                } for offer in popular_items]
            })
        
        return JsonResponse({
            'success': True,
            'quick_sets': quick_sets
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def save_custom_set(request):
    """API endpoint для сохранения пользовательского набора"""
    from django.http import JsonResponse
    import json
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            set_name = data.get('name')
            items = data.get('items', [])
            
            if not set_name or not items:
                return JsonResponse({
                    'success': False,
                    'error': 'Необходимо указать название и товары'
                }, status=400)
            
            # Сохраняем в localStorage (в реальном проекте - в БД)
            custom_sets = json.loads(request.session.get('custom_sets', '[]'))
            
            new_set = {
                'id': len(custom_sets) + 1,
                'name': set_name,
                'description': f'Пользовательский набор: {set_name}',
                'items': items,
                'created_at': timezone.now().isoformat()
            }
            
            custom_sets.append(new_set)
            request.session['custom_sets'] = json.dumps(custom_sets)
            
            return JsonResponse({
                'success': True,
                'set': new_set
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'}, status=405)

def get_custom_sets(request):
    """API endpoint для получения пользовательских наборов"""
    try:
        custom_sets = json.loads(request.session.get('custom_sets', '[]'))
        return JsonResponse({
            'success': True,
            'custom_sets': custom_sets
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def create_category_ajax(request):
    """AJAX view for creating new categories"""
    try:
        category_name = request.POST.get('name', '').strip()
        
        if not category_name:
            return JsonResponse({
                'success': False,
                'error': 'Название категории не может быть пустым'
            })
        
        # Check if category already exists
        if Category.objects.filter(name__iexact=category_name).exists():
            return JsonResponse({
                'success': False,
                'error': 'Категория с таким названием уже существует'
            })
        
        # Create new category
        category = Category.objects.create(
            name=category_name,
            slug=slugify(category_name)
        )
        
        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при создании категории: {str(e)}'
        })

@require_http_methods(["GET"])
def get_categories_ajax(request):
    """AJAX view for getting all categories"""
    try:
        categories = Category.objects.filter(is_active=True).values('id', 'name')
        return JsonResponse({
            'success': True,
            'categories': list(categories)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def add_category(request):
    """View for adding new categories"""
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Категория "{category.name}" успешно создана!')
            # Redirect back to the referring page or to catalog if no referrer
            return redirect(request.META.get('HTTP_REFERER', 'catalog:catalog'))
    else:
        form = CategoryForm()
    
    return render(request, 'catalog/add_category.html', {
        'form': form,
        'title': 'Добавить категорию'
    })

def add_unit(request):
    """View for adding new units"""
    if request.method == 'POST':
        form = UnitForm(request.POST)
        if form.is_valid():
            unit_key = form.cleaned_data['unit_key']
            unit_display = form.cleaned_data['unit_display']
            
            # Store in session to be used in ItemForm
            if 'custom_units' not in request.session:
                request.session['custom_units'] = []
            
            request.session['custom_units'].append({
                'key': unit_key,
                'display': unit_display
            })
            request.session.modified = True
            
            messages.success(request, f'Единица измерения "{unit_display}" успешно добавлена!')
            return redirect(request.META.get('HTTP_REFERER', 'catalog:catalog'))
    else:
        form = UnitForm()
    
    return render(request, 'catalog/add_unit.html', {
        'form': form,
        'title': 'Добавить единицу измерения'
    })
