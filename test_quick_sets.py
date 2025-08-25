import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodsave.settings')
django.setup()

from catalog.models import Offer, Item, Category, Vendor
from catalog.views import get_quick_sets
from django.test import RequestFactory

print('=== ПРОВЕРКА ДАННЫХ ===')
print(f'Offers: {Offer.objects.count()}')
print(f'Items: {Item.objects.count()}')
print(f'Categories: {Category.objects.count()}')
print(f'Vendors: {Vendor.objects.count()}')

# Проверяем активные предложения
active_offers = Offer.objects.filter(is_active=True, status='available')
print(f'Active offers: {active_offers.count()}')

for offer in active_offers[:3]:
    print(f'- {offer.item.title} (${offer.current_price})')

# Тестируем API
factory = RequestFactory()
request = factory.get('/api/quick-sets/')
response = get_quick_sets(request)
print(f'\n=== API RESPONSE ===')
print(f'Status: {response.status_code}')
if hasattr(response, 'content'):
    data = json.loads(response.content.decode())
    print(f'Success: {data.get("success")}')
    print(f'Quick sets: {len(data.get("quick_sets", []))}')
    for qs in data.get('quick_sets', []):
        print(f'- {qs["name"]}: {len(qs["items"])} items')
        for item in qs['items'][:2]:
            print(f'  * {item["title"]} - {item["image_url"]}') 