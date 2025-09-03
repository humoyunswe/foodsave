from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    # Public vendor views
    path('', views.VendorListView.as_view(), name='vendor_list'),
    path('<int:pk>/', views.VendorDetailView.as_view(), name='vendor_detail'),
    
    # Vendor management dashboard
    path('dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('manage/', views.management_hub, name='management_hub'),
    
    # Branch management
    path('<int:vendor_id>/add-branch/', views.add_branch, name='add_branch'),
    
    # Item management
    path('<int:vendor_id>/add-item/', views.add_item, name='add_item'),
    path('<int:vendor_id>/manage-items/', views.manage_items, name='manage_items'),
    
    # Offer management
    path('item/<int:item_id>/add-offer/', views.add_offer, name='add_offer'),
    
    # Admin only
    path('add/', views.add_vendor, name='add_vendor'),
    path('assign-vendor/', views.assign_vendor, name='assign_vendor'),
]
