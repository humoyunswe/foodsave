#!/usr/bin/env python
import os
import sys
import django
from django.test import RequestFactory
import json

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodsave.settings')
django.setup()

from catalog.views import get_recommendations

def test_api_direct():
    print("=== ПРЯМОЕ ТЕСТИРОВАНИЕ ФУНКЦИИ API ===")
    print()
    
    # Создаем mock request
    factory = RequestFactory()
    request = factory.get('/catalog/api/recommendations/')
    
    try:
        # Вызываем функцию напрямую
        response = get_recommendations(request)
        
        print(f"Статус ответа: {response.status_code}")
        print(f"Content-Type: {response.get('Content-Type')}")
        print()
        
        if response.status_code == 200:
            data = response.json() if hasattr(response, 'json') else json.loads(response.content.decode())
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
                    print(f"   Изображение: {rec['image_url']}")
                    print()
            else:
                print("❌ Нет рекомендаций в ответе")
                print(f"Полный ответ: {data}")
        else:
            print(f"❌ Ошибка API: {response.content.decode()}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_direct() 