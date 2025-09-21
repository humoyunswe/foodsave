from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'vendors'

urlpatterns = [
    # Public vendor views
    # path('', views.index, name='index'),
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
    
    # Offer management
    path('item/<int:item_id>/add-offer/', views.add_offer, name='add_offer'),
    path('offer/<int:offer_id>/delete/', views.delete_offer, name='delete_offer'),
    
    # Admin only
    path('add/', views.add_vendor, name='add_vendor'),
    path('assign-vendor/', views.assign_vendor, name='assign_vendor'),
    
    # API endpoints
    path('api/vendors/locations/', views.vendor_locations_api, name='vendor_locations_api'),
]
