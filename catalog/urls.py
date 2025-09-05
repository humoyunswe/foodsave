from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('vendors/', views.CatalogView.as_view(), name='catalog'),
    path('vendors/map/', views.MapView.as_view(), name='map'),
    path('vendors/category/<slug:category_slug>/', views.CategoryView.as_view(), name='category'),
    path('vendors/item/<int:pk>/', views.ItemDetailView.as_view(), name='item_detail'),
    path('vendors/search/', views.SearchView.as_view(), name='search'),
    path('vendors/add-category/', views.add_category, name='add_category'),
    path('add-unit/', views.add_unit, name='add_unit'),
    path('api/recommendations/', views.get_recommendations, name='api_recommendations'),
    path('api/quick-sets/', views.get_quick_sets, name='api_quick_sets'),
    path('api/custom-sets/', views.get_custom_sets, name='api_custom_sets'),
    path('api/save-custom-set/', views.save_custom_set, name='api_save_custom_set'),
    path('api/create-category/', views.create_category_ajax, name='api_create_category'),
    path('api/get-categories/', views.get_categories_ajax, name='api_get_categories'),
]
