#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodsave.settings')
django.setup()

from catalog.models import Item, Offer, Category
from vendors.models import Vendor, Branch
from django.utils import timezone

def check_data():
    print("=== ПРОВЕРКА ДАННЫХ В БД ===")
    print()
    
    # Проверяем количество записей
    print(f"Категории: {Category.objects.count()}")
    print(f"Продавцы: {Vendor.objects.count()}")
    print(f"Филиалы: {Branch.objects.count()}")
    print(f"Товары: {Item.objects.count()}")
    print(f"Предложения: {Offer.objects.count()}")
    print()
    
    # Проверяем активные предложения
    active_offers = Offer.objects.filter(
        is_active=True,
        status='available',
        item__is_active=True,
        item__vendor__is_active=True,
        start_date__lte=timezone.now().date()
    )
    
    print(f"Активные предложения: {active_offers.count()}")
    print()
    
    if active_offers.count() > 0:
        print("=== ПЕРВЫЕ 5 АКТИВНЫХ ПРЕДЛОЖЕНИЙ ===")
        for i, offer in enumerate(active_offers[:5]):
            print(f"{i+1}. {offer.item.title} - {offer.discount_percent}% скидка")
            print(f"   Продавец: {offer.item.vendor.name}")
            print(f"   Цена: {offer.original_price} -> {offer.current_price}")
            print(f"   Статус: {offer.status}")
            print()
    else:
        print("❌ НЕТ АКТИВНЫХ ПРЕДЛОЖЕНИЙ!")
        print()
        
        # Проверяем все предложения
        all_offers = Offer.objects.all()
        print(f"Всего предложений: {all_offers.count()}")
        if all_offers.count() > 0:
            print("=== ВСЕ ПРЕДЛОЖЕНИЯ ===")
            for offer in all_offers:
                print(f"- {offer.item.title}: статус={offer.status}, активен={offer.is_active}")
    
    # Проверяем товары
    print()
    print("=== ТОВАРЫ ===")
    items = Item.objects.all()
    for item in items[:5]:
        print(f"- {item.title} (активен: {item.is_active})")
        print(f"  Продавец: {item.vendor.name if item.vendor else 'Нет'}")
        print(f"  Предложения: {item.offers.count()}")

if __name__ == "__main__":
    check_data() 