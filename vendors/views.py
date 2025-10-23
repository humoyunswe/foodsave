from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from .models import Vendor, Branch
from .forms import VendorForm, BranchForm, OwnerForm, AssignVendorRoleForm, OfferFormWithTime
from catalog.models import Item, Category, ItemImage, Offer, SurpriseBox, SurpriseBoxItem
from catalog.forms import ItemForm, ItemImageFormSet, SurpriseBoxForm
from django import forms

User = get_user_model()

def index(request):
    return render(request, 'vendors/index.html')


class VendorListView(ListView):
    model = Vendor
    template_name = 'vendors/vendor_list.html'
    context_object_name = 'vendors'
    paginate_by = 12
    
    def get_queryset(self):
        return Vendor.objects.filter(is_active=True).prefetch_related('branches')


def vendor_detail(request, pk):
    from django.db.models import Q
    from django.utils import timezone
    
    vendor = get_object_or_404(
        Vendor.objects.filter(is_active=True).prefetch_related('branches', 'items'),
        pk=pk
    )
    
    # Get active branches with coordinates
    branches = vendor.branches.filter(is_active=True).order_by('name')
    
    # Get active items with their offers and images (exclude expired items)
    items = vendor.items.filter(
        is_active=True
    ).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gt=timezone.now().date())
    ).select_related('category', 'branch').prefetch_related(
        'images', 
        'offers'
    ).order_by('-created_at')[:12]
    
    # Prepare branches data for JavaScript (with coordinates)
    branches_data = []
    for branch in branches:
        branches_data.append({
            'id': branch.id,
            'name': branch.name,
            'address': branch.address,
            'latitude': float(branch.latitude) if branch.latitude else None,
            'longitude': float(branch.longitude) if branch.longitude else None,
            'phone': branch.phone,
            'is_open': branch.is_open_now(),
            'hours': branch.get_today_hours()
        })
    
    context = {
        'vendor': vendor,
        'items': items,
        'branches': branches,
        'branches_json': branches_data,  # For JavaScript
    }
    return render(request, 'vendors/vendor_detail.html', context)



@login_required
def vendor_dashboard(request):
    """Vendor dashboard showing their businesses"""
    user_vendors = Vendor.objects.filter(owner=request.user).prefetch_related('branches', 'items')
    return render(request, 'vendors/dashboard.html', {'vendors': user_vendors})


@login_required
def add_branch(request, vendor_id):
    """Add a new branch to vendor"""
    # Суперадмин может добавлять филиалы любому вендору
    if request.user.is_superuser:
        vendor = get_object_or_404(Vendor, id=vendor_id)
    else:
        vendor = get_object_or_404(Vendor, id=vendor_id, owner=request.user)
    
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.vendor = vendor
            
            # Process opening hours from POST data
            opening_hours = {}
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            for day in days:
                is_enabled = request.POST.get(f'day_{day}')
                if is_enabled == 'on':
                    open_time = request.POST.get(f'open_{day}')
                    close_time = request.POST.get(f'close_{day}')
                    if open_time and close_time:
                        opening_hours[day] = f"{open_time}-{close_time}"
                    else:
                        opening_hours[day] = "closed"
                else:
                    opening_hours[day] = "closed"
            
            branch.opening_hours = opening_hours
            branch.save()
            messages.success(request, f'Филиал "{branch.name}" успешно добавлен!')
            return redirect('vendors:vendor_dashboard')
        else:
            # Add debug information
            print("Form errors:", form.errors)
            for field, errors in form.errors.items():
                messages.error(request, f'{field}: {", ".join(errors)}')
    else:
        form = BranchForm()
    
    # Generate time choices for template
    time_choices = [(f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}") 
                    for h in range(24) for m in [0, 30]]
    
    return render(request, 'vendors/add_branch.html', {
        'form': form, 
        'vendor': vendor,
        'time_choices': time_choices
    })


@login_required
def add_item(request, vendor_id):
    """Add a new item/product to vendor"""
    # Суперадмин может добавлять товары любому вендору
    if request.user.is_superuser:
        vendor = get_object_or_404(Vendor, id=vendor_id)
    else:
        vendor = get_object_or_404(Vendor, id=vendor_id, owner=request.user)
    
    # Check if vendor has branches
    if not vendor.branches.exists():
        messages.error(request, 'Сначала добавьте филиал для вашего заведения.')
        return redirect('vendors:add_branch', vendor_id=vendor.id)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, vendor=vendor, request=request)
        image_formset = ItemImageFormSet(request.POST, request.FILES)
        
        if form.is_valid() and image_formset.is_valid():
            item = form.save(commit=False)
            item.vendor = vendor
            item.save()
            
            # Save images
            image_formset.instance = item
            image_formset.save()
            
            messages.success(request, f'Товар "{item.title}" успешно добавлен!')
            
            # Check if user wants to add offer immediately
            if 'save_and_add_offer' in request.POST:
                return redirect('vendors:add_offer', item_id=item.id)
            
            return redirect('vendors:vendor_dashboard')
    else:
        form = ItemForm(vendor=vendor, request=request)
        image_formset = ItemImageFormSet()
    
    return render(request, 'vendors/add_item.html', {
        'form': form,
        'image_formset': image_formset,
        'vendor': vendor
    })


@login_required
def add_offer(request, item_id):
    """Add an offer to an item with time fields"""
    # Суперадмин может добавлять предложения к любым товарам
    if request.user.is_superuser:
        item = get_object_or_404(Item, id=item_id)
    else:
        item = get_object_or_404(Item, id=item_id, vendor__owner=request.user)
    vendor = item.vendor
    
    if request.method == 'POST':
        form = OfferFormWithTime(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.item = item
            # inherit branch from the item
            offer.branch = item.branch
            offer.save()
            messages.success(request, f'Предложение для "{item.title}" создано!')
            return redirect('vendors:manage_items', vendor_id=vendor.id)
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = OfferFormWithTime()
    
    return render(request, 'vendors/add_offer.html', {
        'form': form,
        'item': item
    })


@login_required
def manage_items(request, vendor_id):
    """Manage vendor items"""
    vendor = get_object_or_404(Vendor, id=vendor_id, owner=request.user)
    items = Item.objects.filter(vendor=vendor).select_related('category', 'branch').prefetch_related('images', 'offers')
    
    # Handle search and filtering
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        items = items.filter(title__icontains=search_query)
    
    if category_filter:
        items = items.filter(category_id=category_filter)
    
    if status_filter == 'active':
        items = items.filter(is_active=True)
    elif status_filter == 'inactive':
        items = items.filter(is_active=False)
    
    # Get categories for filter dropdown
    from catalog.models import Category
    categories = Category.objects.filter(is_active=True)
    
    return render(request, 'vendors/manage_items.html', {
        'vendor': vendor,
        'items': items,
        'categories': categories
    })


@staff_member_required
def add_vendor(request):
    if request.method == 'POST':
        # Handle owner creation via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            owner_form = OwnerForm(request.POST)
            if owner_form.is_valid():
                owner = owner_form.save()
                return JsonResponse({
                    'success': True,
                    'owner_id': owner.id,
                    'owner_name': f"{owner.first_name} {owner.last_name} ({owner.username})"
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': owner_form.errors
                })
        
        # Handle vendor creation
        form = VendorForm(request.POST, request.FILES)
        if form.is_valid():
            vendor = form.save()
            messages.success(request, f'Vendor "{vendor.name}" успешно создан!')
            return redirect('vendors:vendor_list')
    else:
        form = VendorForm()
    
    owner_form = OwnerForm()
    return render(request, 'vendors/add_vendor.html', {
        'form': form,
        'owner_form': owner_form
    })


@login_required
def management_hub(request):
    """Unified management hub with shortcuts to vendor actions"""
    user_vendors = Vendor.objects.filter(owner=request.user).prefetch_related('branches', 'items')
    return render(request, 'vendors/management.html', {
        'vendors': user_vendors,
    })


@login_required
def edit_item(request, item_id):
    """Edit an existing item"""
    # Суперадмин может редактировать любые товары
    if request.user.is_superuser:
        item = get_object_or_404(Item, id=item_id)
    else:
        item = get_object_or_404(Item, id=item_id, vendor__owner=request.user)
    vendor = item.vendor
    
    if request.method == 'POST':
        print(f"POST request received for item {item_id}")
        print(f"POST data: {request.POST}")
        
        form = ItemForm(request.POST, instance=item, vendor=vendor, request=request)
        image_formset = ItemImageFormSet(request.POST, request.FILES, instance=item)
        
        print(f"Form is valid: {form.is_valid()}")
        print(f"Formset is valid: {image_formset.is_valid()}")
        
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
        if not image_formset.is_valid():
            print(f"Formset errors: {image_formset.errors}")
        
        if form.is_valid() and image_formset.is_valid():
            print("Saving form and formset...")
            item = form.save()
            image_formset.save()
            messages.success(request, f'Товар "{item.title}" успешно обновлен!')
            return redirect('vendors:manage_items', vendor_id=vendor.id)
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = ItemForm(instance=item, vendor=vendor, request=request)
        image_formset = ItemImageFormSet(instance=item)
    
    return render(request, 'vendors/edit_item.html', {
        'form': form,
        'image_formset': image_formset,
        'item': item,
        'vendor': vendor
    })


@login_required
def delete_item(request, item_id):
    """Delete an item"""
    # Суперадмин может удалять любые товары
    if request.user.is_superuser:
        item = get_object_or_404(Item, id=item_id)
    else:
        item = get_object_or_404(Item, id=item_id, vendor__owner=request.user)
    vendor = item.vendor
    
    if request.method == 'POST':
        item_title = item.title
        item.delete()
        messages.success(request, f'Товар "{item_title}" успешно удален!')
        return redirect('vendors:manage_items', vendor_id=vendor.id)
    
    return render(request, 'vendors/delete_item.html', {
        'item': item,
        'vendor': vendor
    })


@staff_member_required
def assign_vendor(request):
    """Staff page to assign vendor role to an existing user"""
    if request.method == 'POST':
        form = AssignVendorRoleForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Пользователь {user.username} назначен как вендор.')
            return redirect('vendors:assign_vendor')
    else:
        form = AssignVendorRoleForm()

    return render(request, 'vendors/assign_vendor.html', { 'form': form })


def vendor_locations_api(request):
    """API endpoint to get vendor locations for map display"""
    vendors = Vendor.objects.filter(is_active=True).prefetch_related('branches')
    
    vendor_data = []
    for vendor in vendors:
        branches_data = []
        for branch in vendor.branches.filter(is_active=True):
            if branch.latitude and branch.longitude:
                branches_data.append({
                    'id': branch.id,
                    'name': branch.name,
                    'address': branch.address,
                    'phone': branch.phone,
                    'latitude': str(branch.latitude),
                    'longitude': str(branch.longitude)
                })
        
        if branches_data:  # Only include vendors with branches that have coordinates
            vendor_data.append({
                'id': vendor.id,
                'name': vendor.name,
                'branches': branches_data
            })
    
    return JsonResponse({'vendors': vendor_data})


@login_required
def delete_offer(request, offer_id):
    """Delete an offer"""
    # Суперадмин может удалять любые предложения
    if request.user.is_superuser:
        offer = get_object_or_404(Offer, id=offer_id)
    else:
        offer = get_object_or_404(Offer, id=offer_id, item__vendor__owner=request.user)
    vendor = offer.item.vendor
    
    if request.method == 'POST':
        offer_title = f"{offer.item.title} - {offer.discount_percent}% скидка"
        offer.delete()
        messages.success(request, f'Предложение "{offer_title}" успешно удалено!')
        return redirect('vendors:manage_items', vendor_id=vendor.id)
    
    return render(request, 'vendors/delete_offer.html', {
        'offer': offer,
        'vendor': vendor
    })


@login_required
def create_surprise_box(request, vendor_id):
    """Create a new surprise box"""
    vendor = get_object_or_404(Vendor, id=vendor_id, owner=request.user)
    
    if request.method == 'POST':
        form = SurpriseBoxForm(request.POST, request.FILES, vendor=vendor)
        if form.is_valid():
            surprise_box = form.save(commit=False)
            surprise_box.vendor = vendor
            surprise_box.save()
            
            # Save the selected items to the box with quantities
            selected_items = form.cleaned_data['items']
            for item in selected_items:
                # Get quantity from POST data (sent by JavaScript)
                quantity_key = f'item_quantity_{item.id}'
                quantity = int(request.POST.get(quantity_key, 1))
                
                SurpriseBoxItem.objects.create(
                    surprise_box=surprise_box,
                    item=item,
                    quantity=quantity
                )
            
            messages.success(request, f'Сюрприз бокс "{surprise_box.title}" успешно создан!')
            return redirect('vendors:manage_surprise_boxes', vendor_id=vendor.id)
    else:
        form = SurpriseBoxForm(vendor=vendor)
    
    # Get vendor items with additional info for cards (exclude expired items)
    from django.db.models import Q
    from django.utils import timezone
    vendor_items = vendor.items.filter(
        is_active=True
    ).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gt=timezone.now().date())
    ).select_related('category').prefetch_related('images')
    
    return render(request, 'vendors/create_surprise_box.html', {
        'form': form,
        'vendor': vendor,
        'vendor_items': vendor_items
    })


@login_required
def manage_surprise_boxes(request, vendor_id):
    """Manage vendor's surprise boxes"""
    vendor = get_object_or_404(Vendor, id=vendor_id, owner=request.user)
    surprise_boxes = SurpriseBox.objects.filter(vendor=vendor).order_by('-created_at')
    
    return render(request, 'vendors/manage_surprise_boxes.html', {
        'vendor': vendor,
        'surprise_boxes': surprise_boxes
    })


@login_required
def edit_surprise_box(request, vendor_id, box_id):
    """Edit an existing surprise box"""
    vendor = get_object_or_404(Vendor, id=vendor_id, owner=request.user)
    surprise_box = get_object_or_404(SurpriseBox, id=box_id, vendor=vendor)
    
    if request.method == 'POST':
        form = SurpriseBoxForm(request.POST, request.FILES, instance=surprise_box, vendor=vendor)
        if form.is_valid():
            surprise_box = form.save()
            
            # Update items in the box
            # First, remove existing items
            SurpriseBoxItem.objects.filter(surprise_box=surprise_box).delete()
            
            # Then add new items
            selected_items = form.cleaned_data['items']
            for item in selected_items:
                SurpriseBoxItem.objects.create(
                    surprise_box=surprise_box,
                    item=item,
                    quantity=1
                )
            
            messages.success(request, f'Сюрприз бокс "{surprise_box.title}" успешно обновлен!')
            return redirect('vendors:manage_surprise_boxes', vendor_id=vendor.id)
    else:
        # Pre-populate the items field with current items
        form = SurpriseBoxForm(instance=surprise_box, vendor=vendor)
        form.fields['items'].initial = surprise_box.items.all()
    
    return render(request, 'vendors/edit_surprise_box.html', {
        'form': form,
        'vendor': vendor,
        'surprise_box': surprise_box
    })


@login_required
def delete_surprise_box(request, vendor_id, box_id):
    """Delete a surprise box"""
    vendor = get_object_or_404(Vendor, id=vendor_id, owner=request.user)
    surprise_box = get_object_or_404(SurpriseBox, id=box_id, vendor=vendor)
    
    if request.method == 'POST':
        box_title = surprise_box.title
        surprise_box.delete()
        messages.success(request, f'Сюрприз бокс "{box_title}" успешно удален!')
        return redirect('vendors:manage_surprise_boxes', vendor_id=vendor.id)
    
    return render(request, 'vendors/delete_surprise_box.html', {
        'surprise_box': surprise_box,
        'vendor': vendor
    })


@login_required
def surprise_box_detail(request, vendor_id, box_id):
    """View surprise box details"""
    vendor = get_object_or_404(Vendor, id=vendor_id, owner=request.user)
    surprise_box = get_object_or_404(SurpriseBox, id=box_id, vendor=vendor)
    box_items = SurpriseBoxItem.objects.filter(surprise_box=surprise_box).select_related('item')
    
    return render(request, 'vendors/surprise_box_detail.html', {
        'vendor': vendor,
        'surprise_box': surprise_box,
        'box_items': box_items
    })


@login_required
@require_POST
def toggle_item_status(request, item_id):
    """Toggle item active/inactive status via AJAX"""
    import json
    from django.utils import timezone
    
    item = get_object_or_404(Item, id=item_id, vendor__owner=request.user)
    
    # If trying to activate an expired item, request new expiry date
    if not item.is_active and item.is_expired():
        # Check if new expiry date is provided
        try:
            data = json.loads(request.body) if request.body else {}
            new_expiry_date = data.get('new_expiry_date')
            
            if not new_expiry_date:
                return JsonResponse({
                    'success': False,
                    'require_expiry': True,
                    'message': 'Срок годности истек. Необходимо указать новый срок годности.',
                    'current_expiry': item.expiry_date.isoformat() if item.expiry_date else None
                })
            
            # Update expiry date
            from datetime import datetime
            item.expiry_date = datetime.strptime(new_expiry_date, '%Y-%m-%d').date()
        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse({
                'success': False,
                'message': 'Неверный формат даты'
            })
    
    # Toggle the status
    item.is_active = not item.is_active
    item.save()
    
    return JsonResponse({
        'success': True,
        'is_active': item.is_active,
        'status_text': 'Активен' if item.is_active else 'Неактивен',
        'message': f'Товар "{item.title}" {"активирован" if item.is_active else "деактивирован"}',
        'expiry_date': item.expiry_date.isoformat() if item.expiry_date else None
    })

from django.utils import timezone


@login_required
def edit_offer(request, offer_id):
    """Edit an existing offer"""
    # Суперадмин может редактировать любое предложение
    if request.user.is_superuser:
        offer = get_object_or_404(Offer, id=offer_id)
    else:
        offer = get_object_or_404(Offer, id=offer_id, item__vendor__owner=request.user)
    
    item = offer.item
    vendor = item.vendor
    
    if request.method == 'POST':
        form = OfferFormWithTime(request.POST, instance=offer)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.item = item
            offer.branch = item.branch
            offer.save()
            messages.success(request, f'Предложение для "{item.title}" успешно обновлено!')
            
            # Перенаправление в зависимости от роли пользователя
            if request.user.is_superuser:
                return redirect('vendors:admin_item_edit', vendor_id=vendor.id, item_id=item.id)
            else:
                return redirect('vendors:manage_items', vendor_id=vendor.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = OfferFormWithTime(instance=offer)
    
    return render(request, 'vendors/edit_offer.html', {
        'form': form,
        'offer': offer,
        'item': item,
        'vendor': vendor
    })


# ==================== ADMIN PANEL VIEWS ====================

@login_required
def admin_vendor_list(request):
    """Список всех вендоров для суперадмина"""
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав доступа к этой странице.')
        return redirect('catalog:catalog')
    
    vendors = Vendor.objects.all().annotate(
        items_count=Count('items'),
        branches_count=Count('branches'),
        active_items_count=Count('items', filter=Q(items__is_active=True))
    ).order_by('-created_at')
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        vendors = vendors.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(owner__username__icontains=search_query) |
            Q(owner__email__icontains=search_query)
        )
    
    # Фильтр по статусу
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        vendors = vendors.filter(is_active=True)
    elif status_filter == 'inactive':
        vendors = vendors.filter(is_active=False)
    
    context = {
        'vendors': vendors,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_vendors': vendors.count(),
        'active_vendors': vendors.filter(is_active=True).count(),
    }
    
    return render(request, 'vendors/admin/vendor_list.html', context)


@login_required
def admin_vendor_detail(request, vendor_id):
    """Детальная информация о вендоре для админа"""
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав доступа к этой странице.')
        return redirect('catalog:catalog')
    
    vendor = get_object_or_404(Vendor, id=vendor_id)
    
    # Статистика
    stats = {
        'total_items': vendor.items.count(),
        'active_items': vendor.items.filter(is_active=True).count(),
        'total_branches': vendor.branches.count(),
        'active_branches': vendor.branches.filter(is_active=True).count(),
        'total_offers': Offer.objects.filter(item__vendor=vendor).count(),
        'active_offers': Offer.objects.filter(item__vendor=vendor, is_active=True).count(),
    }
    
    # Последние товары
    recent_items = vendor.items.order_by('-created_at')[:10]
    
    # Последние филиалы
    recent_branches = vendor.branches.order_by('-created_at')[:5]
    
    context = {
        'vendor': vendor,
        'stats': stats,
        'recent_items': recent_items,
        'recent_branches': recent_branches,
    }
    
    return render(request, 'vendors/admin/vendor_detail.html', context)


@login_required
def admin_vendor_items(request, vendor_id):
    """Управление товарами вендора для админа"""
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав доступа к этой странице.')
        return redirect('catalog:catalog')
    
    vendor = get_object_or_404(Vendor, id=vendor_id)
    
    # Получаем товары через филиалы вендора
    from catalog.models import Item
    items = Item.objects.filter(
        branch__vendor=vendor
    ).select_related('category', 'branch', 'vendor').prefetch_related('images', 'offers').order_by('-created_at')
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        items = items.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Фильтр по статусу
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        items = items.filter(is_active=True)
    elif status_filter == 'inactive':
        items = items.filter(is_active=False)
    
    context = {
        'vendor': vendor,
        'items': items,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'vendors/admin/vendor_items.html', context)


@login_required
def admin_vendor_branches(request, vendor_id):
    """Управление филиалами вендора для админа"""
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав доступа к этой странице.')
        return redirect('catalog:catalog')
    
    vendor = get_object_or_404(Vendor, id=vendor_id)
    branches = vendor.branches.order_by('-created_at')
    
    # Поиск
    search_query = request.GET.get('search', '')
    if search_query:
        branches = branches.filter(
            Q(name__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    context = {
        'vendor': vendor,
        'branches': branches,
        'search_query': search_query,
    }
    
    return render(request, 'vendors/admin/vendor_branches.html', context)


@login_required
def admin_vendor_edit(request, vendor_id):
    """Редактирование вендора для админа"""
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав доступа к этой странице.')
        return redirect('catalog:catalog')
    
    vendor = get_object_or_404(Vendor, id=vendor_id)
    
    if request.method == 'POST':
        form = VendorForm(request.POST, request.FILES, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Вендор "{vendor.name}" успешно обновлен.')
            return redirect('vendors:admin_vendor_detail', vendor_id=vendor.id)
    else:
        form = VendorForm(instance=vendor)
    
    context = {
        'vendor': vendor,
        'form': form,
    }
    
    return render(request, 'vendors/admin/vendor_edit.html', context)


@login_required
def admin_vendor_toggle_status(request, vendor_id):
    """Переключение статуса вендора"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Нет прав доступа'}, status=403)
    
    vendor = get_object_or_404(Vendor, id=vendor_id)
    vendor.is_active = not vendor.is_active
    vendor.save()
    
    status = 'активен' if vendor.is_active else 'неактивен'
    messages.success(request, f'Вендор "{vendor.name}" теперь {status}.')
    
    return JsonResponse({
        'success': True,
        'is_active': vendor.is_active,
        'status_text': status
    })


@login_required
def admin_item_edit(request, vendor_id, item_id):
    """Редактирование товара вендора для админа"""
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав доступа к этой странице.')
        return redirect('catalog:catalog')
    
    vendor = get_object_or_404(Vendor, id=vendor_id)
    item = get_object_or_404(Item, id=item_id, vendor=vendor)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Товар "{item.title}" успешно обновлен.')
            return redirect('vendors:admin_vendor_items', vendor_id=vendor.id)
    else:
        form = ItemForm(instance=item)
    
    context = {
        'vendor': vendor,
        'item': item,
        'form': form,
    }
    
    return render(request, 'vendors/admin/item_edit.html', context)


@login_required
def admin_branch_edit(request, vendor_id, branch_id):
    """Редактирование филиала вендора для админа"""
    if not request.user.is_superuser:
        messages.error(request, 'У вас нет прав доступа к этой странице.')
        return redirect('catalog:catalog')
    
    vendor = get_object_or_404(Vendor, id=vendor_id)
    branch = get_object_or_404(Branch, id=branch_id, vendor=vendor)
    
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, f'Филиал "{branch.name}" успешно обновлен.')
            return redirect('vendors:admin_vendor_branches', vendor_id=vendor.id)
    else:
        form = BranchForm(instance=branch)
    
    context = {
        'vendor': vendor,
        'branch': branch,
        'form': form,
    }
    
    return render(request, 'vendors/admin/branch_edit.html', context)
