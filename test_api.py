#!/usr/bin/env python
import os
import sys
import django
import requests
import json

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodsave.settings')
django.setup()

def test_api():
    print("=== ТЕСТИРОВАНИЕ API РЕКОМЕНДАЦИЙ ===")
    print()
    
    try:
        # Тестируем API
        response = requests.get('http://localhost:8000/catalog/api/recommendations/')
        
        print(f"Статус ответа: {response.status_code}")
        print(f"Заголовки: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            print(f"Успех: {data.get('success')}")
            print(f"Количество рекомендаций: {len(data.get('recommendations', []))}")
            print()
            
            if data.get('recommendations'):
                print("=== ПЕРВЫЕ 3 РЕКОМЕНДАЦИИ ===")
                for i, rec in enumerate(data['recommendations'][:3]):
                    print(f"{i+1}. {rec['title']}")
                    print(f"   Продавец: {rec['vendor_name']}")
                    print(f"   Цена: {rec['original_price']} -> {rec['current_price']} сум")
                    print(f"   Скидка: {rec['discount_percent']}%")
                    print(f"   Бейдж: {rec['badge_type']} - {rec['badge_text']}")
                    print()
            else:
                print("❌ Нет рекомендаций в ответе")
        else:
            print(f"❌ Ошибка API: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Не удалось подключиться к серверу")
        print("Убедитесь, что сервер запущен: python manage.py runserver")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_api() 