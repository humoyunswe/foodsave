from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from .models import Vendor, Branch
from .forms import VendorForm, BranchForm, OwnerForm, AssignVendorRoleForm
from catalog.models import Item, Category, ItemImage, Offer
from catalog.forms import ItemForm, ItemImageFormSet, OfferForm
from django import forms


class VendorListView(ListView):
    model = Vendor
    template_name = 'vendors/vendor_list.html'
    context_object_name = 'vendors'
    paginate_by = 12
    
    def get_queryset(self):
        return Vendor.objects.filter(is_active=True).prefetch_related('branches')


class VendorDetailView(DetailView):
    model = Vendor
    template_name = 'vendors/vendor_detail.html'
    context_object_name = 'vendor'
    
    def get_queryset(self):
        return Vendor.objects.filter(is_active=True).prefetch_related('branches', 'items')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.filter(is_active=True)[:12]
        context['branches'] = self.object.branches.filter(is_active=True)
        return context


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
        form = ItemForm(request.POST, vendor=vendor)
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
        form = ItemForm(vendor=vendor)
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
        form = OfferForm(request.POST, vendor=vendor)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.item = item
            offer.save()
            messages.success(request, f'Предложение для "{item.title}" создано!')
            return redirect('vendors:manage_items', vendor_id=vendor.id)
    else:
        form = OfferForm(vendor=vendor)
    
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