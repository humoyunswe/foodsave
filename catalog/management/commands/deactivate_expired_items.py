from django.core.management.base import BaseCommand
from django.utils import timezone
from catalog.models import Item


class Command(BaseCommand):
    help = 'Деактивирует товары с истекшим сроком годности'

    def handle(self, *args, **options):
        """
        Автоматически деактивирует товары с истекшим сроком годности
        Эту команду можно запускать через cron каждый день
        """
        today = timezone.now().date()
        
        # Найти все активные товары с истекшим сроком
        expired_items = Item.objects.filter(
            is_active=True,
            expiry_date__isnull=False,
            expiry_date__lt=today
        )
        
        count = expired_items.count()
        
        if count > 0:
            # Деактивировать все просроченные товары
            expired_items.update(is_active=False)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Деактивировано {count} просроченных товаров'
                )
            )
            
            # Вывести список деактивированных товаров
            for item in expired_items:
                self.stdout.write(
                    f'  - {item.title} (срок: {item.expiry_date}) от {item.vendor.name}'
                )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  Просроченных товаров не найдено')
            )
        
        # Также проверить и деактивировать истекшие предложения
        from catalog.models import Offer
        expired_offers = Offer.objects.filter(
            is_active=True,
            end_date__isnull=False,
            end_date__lt=today
        )
        
        offer_count = expired_offers.count()
        if offer_count > 0:
            expired_offers.update(is_active=False, status='expired')
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Деактивировано {offer_count} истекших предложений'
                )
            )


