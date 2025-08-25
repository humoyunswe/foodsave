#!/usr/bin/env python
import os
import sys
import django
from datetime import date, timedelta

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodsave.settings')
django.setup()

from catalog.models import Item, Offer
from vendors.models import Vendor, Branch
from decimal import Decimal

def create_test_offers():
    print("=== СОЗДАНИЕ ТЕСТОВЫХ ПРЕДЛОЖЕНИЙ ===")
    print()
    
    # Получаем все товары
    items = Item.objects.filter(is_active=True)
    print(f"Найдено товаров: {items.count()}")
    
    if items.count() == 0:
        print("❌ Нет активных товаров!")
        return
    
    # Получаем первый филиал для каждого продавца
    branches = {}
    for vendor in Vendor.objects.filter(is_active=True):
        branch = vendor.branches.filter(is_active=True).first()
        if branch:
            branches[vendor] = branch
    
    if not branches:
        print("❌ Нет активных филиалов!")
        return
    
    offers_created = 0
    
    for item in items:
        vendor = item.vendor
        if vendor not in branches:
            print(f"⚠️ Пропускаем {item.title} - нет филиала для {vendor.name}")
            continue
        
        branch = branches[vendor]
        
        # Создаем предложение с разными скидками
        discount_percent = 25 if "молоко" in item.title.lower() else 30 if "сыр" in item.title.lower() else 20
        
        # Создаем базовую цену (примерная)
        base_price = Decimal('15000') if "молоко" in item.title.lower() else Decimal('25000') if "сыр" in item.title.lower() else Decimal('8000')
        
        # Проверяем, есть ли уже предложение для этого товара
        existing_offer = Offer.objects.filter(item=item, branch=branch).first()
        if existing_offer:
            print(f"⚠️ Предложение для {item.title} уже существует")
            continue
        
        # Создаем новое предложение
        offer = Offer.objects.create(
            item=item,
            branch=branch,
            original_price=base_price,
            discount_percent=discount_percent,
            quantity=10,  # Ограниченное количество
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),  # Действует неделю
            is_active=True,
            status='available'
        )
        
        print(f"✅ Создано предложение для {item.title}")
        print(f"   Цена: {base_price} -> {offer.current_price} сум")
        print(f"   Скидка: {discount_percent}%")
        print(f"   Филиал: {branch.name}")
        print()
        
        offers_created += 1
    
    print(f"=== РЕЗУЛЬТАТ ===")
    print(f"Создано предложений: {offers_created}")
    print(f"Всего предложений в БД: {Offer.objects.count()}")

if __name__ == "__main__":
    create_test_offers() 