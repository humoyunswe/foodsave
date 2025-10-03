from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Vendor, Branch
from .forms import VendorForm, BranchForm, OwnerForm, AssignVendorRoleForm
from catalog.models import Item, Category, ItemImage, Offer, SurpriseBox, SurpriseBoxItem
from catalog.forms import ItemForm, ItemImageFormSet, OfferForm, SurpriseBoxForm
from django import forms

def index(request):
    return render(request, 'vendors/index.html')


class VendorListView(ListView):
    model = Vendor
    template_name = 'vendors/vendor_list.html'
    context_object_name = 'vendors'
    paginate_by = 12
    
    def get_queryset(self):
        return Vendor.objects.filter(is_active=True).prefetch_related('branches')


# class VendorDetailView(DetailView):
#     model = Vendor
#     template_name = 'vendors/vendor_detail.html'
#     context_object_name = 'vendor'
    
#     def get_queryset(self):
#         return Vendor.objects.filter(is_active=True).prefetch_related('branches', 'items')
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['items'] = self.object.items.filter(is_active=True)[:12]
#         context['branches'] = self.object.branches.filter(is_active=True)
#         return context

def vendor_detail(request, pk):
    vendor = get_object_or_404(
        Vendor.objects.filter(is_active=True).prefetch_related('branches', 'items'),
        pk=pk
    )
    
    # Get active branches with coordinates
    branches = vendor.branches.filter(is_active=True).order_by('name')
    
    # Get active items with their offers and images
    items = vendor.items.filter(is_active=True).select_related('category', 'branch').prefetch_related(
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
    vendor = get_object_or_404(Vendor, id=vendor_id, owner=request.user)
    
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.vendor = vendor
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
    
    return render(request, 'vendors/add_branch.html', {
        'form': form, 
        'vendor': vendor
    })


@login_required
def add_item(request, vendor_id):
    """Add a new item/product to vendor"""
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
    """Add an offer to an item"""
    item = get_object_or_404(Item, id=item_id, vendor__owner=request.user)
    vendor = item.vendor
    
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.item = item
            # inherit branch from the item
            offer.branch = item.branch
            offer.save()
            messages.success(request, f'Предложение для "{item.title}" создано!')
            return redirect('vendors:manage_items', vendor_id=vendor.id)
    else:
        form = OfferForm()
    
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
    
    # Get vendor items with additional info for cards
    vendor_items = vendor.items.filter(is_active=True).select_related('category').prefetch_related('images')
    
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