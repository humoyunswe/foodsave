from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'vendors'

urlpatterns = [
    # Public vendor views
    path('vendors-list/', views.VendorListView.as_view(), name='vendor_list'),
    path('vendors/<int:pk>/', views.vendor_detail, name='vendor_detail'),
    
    # Vendor management dashboard
    path('dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('manage/', views.management_hub, name='management_hub'),
    
    # Branch management
    path('<int:vendor_id>/add-branch/', views.add_branch, name='add_branch'),
    
    # Item management
    path('<int:vendor_id>/add-item/', views.add_item, name='add_item'),
    path('<int:vendor_id>/manage-items/', views.manage_items, name='manage_items'),
    path('item/<int:item_id>/edit/', views.edit_item, name='edit_item'),
    path('item/<int:item_id>/delete/', views.delete_item, name='delete_item'),
    path('item/<int:item_id>/toggle-status/', views.toggle_item_status, name='toggle_item_status'),
    
    # Offer management
    path('item/<int:item_id>/add-offer/', views.add_offer, name='add_offer'),
    path('offer/<int:offer_id>/edit/', views.edit_offer, name='edit_offer'),  # НОВЫЙ МАРШРУТ
    path('offer/<int:offer_id>/delete/', views.delete_offer, name='delete_offer'),
    
    # Surprise Box management
    path('<int:vendor_id>/create-surprise-box/', views.create_surprise_box, name='create_surprise_box'),
    path('<int:vendor_id>/manage-surprise-boxes/', views.manage_surprise_boxes, name='manage_surprise_boxes'),
    path('<int:vendor_id>/surprise-box/<int:box_id>/', views.surprise_box_detail, name='surprise_box_detail'),
    path('<int:vendor_id>/surprise-box/<int:box_id>/edit/', views.edit_surprise_box, name='edit_surprise_box'),
    path('<int:vendor_id>/surprise-box/<int:box_id>/delete/', views.delete_surprise_box, name='delete_surprise_box'),
    
    # Admin only
    path('add/', views.add_vendor, name='add_vendor'),
    path('assign-vendor/', views.assign_vendor, name='assign_vendor'),
    
    # Super Admin Panel
    path('admin/vendors/', views.admin_vendor_list, name='admin_vendor_list'),
    path('admin/vendors/<int:vendor_id>/', views.admin_vendor_detail, name='admin_vendor_detail'),
    path('admin/vendors/<int:vendor_id>/edit/', views.admin_vendor_edit, name='admin_vendor_edit'),
    path('admin/vendors/<int:vendor_id>/toggle-status/', views.admin_vendor_toggle_status, name='admin_vendor_toggle_status'),
    path('admin/vendors/<int:vendor_id>/items/', views.admin_vendor_items, name='admin_vendor_items'),
    path('admin/vendors/<int:vendor_id>/branches/', views.admin_vendor_branches, name='admin_vendor_branches'),
    path('admin/vendors/<int:vendor_id>/items/<int:item_id>/edit/', views.admin_item_edit, name='admin_item_edit'),
    path('admin/vendors/<int:vendor_id>/branches/<int:branch_id>/edit/', views.admin_branch_edit, name='admin_branch_edit'),
    
    # API endpoints
    path('api/vendors/locations/', views.vendor_locations_api, name='vendor_locations_api'),
]