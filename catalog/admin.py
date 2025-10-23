from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Category, Item, ItemImage, Offer


class ItemImageInline(admin.TabularInline):
    model = ItemImage
    extra = 1
    fields = ('image', 'is_primary', 'order')


class OfferInline(admin.TabularInline):
    model = Offer
    extra = 0
    fields = ('branch', 'original_price', 'discount_percent', 'quantity', 'start_date', 'end_date', 'is_active', 'status')
    readonly_fields = ('current_price',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'items_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    
    def items_count(self, obj):
        count = obj.item_set.count()
        if count > 0:
            return format_html(
                '<a href="/admin/catalog/item/?category__id__exact={}">{} items</a>',
                obj.id, count
            )
        return "0 items"
    items_count.short_description = "Items"


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'title', 'vendor', 'branch', 'category', 'unit', 'is_active', 'offers_count', 'created_at')
    list_filter = ('vendor__type', 'category', 'unit', 'is_active', 'created_at')
    search_fields = ('title', 'description', 'vendor__name', 'branch__name')
    ordering = ('-created_at',)
    inlines = [ItemImageInline, OfferInline]
    list_per_page = 25
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('vendor', 'branch', 'category', 'title', 'description')
        }),
        ('Дополнительная информация', {
            'fields': ('unit', 'expiry_date', 'original_price'),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def image_preview(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 8px; object-fit: cover;" />',
                primary_image.image.url
            )
        elif obj.images.exists():
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 8px; object-fit: cover;" />',
                obj.images.first().image.url
            )
        return format_html(
            '<div style="width: 50px; height: 50px; background: #f8f9fa; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #6c757d;">📦</div>'
        )
    image_preview.short_description = "Изображение"
    
    def offers_count(self, obj):
        count = obj.offers.count()
        active_count = obj.offers.filter(status='available').count()
        if count > 0:
            return format_html(
                '<a href="/admin/catalog/offer/?item__id__exact={}" style="color: #198754; text-decoration: none;">{} всего ({} активных)</a>',
                obj.id, count, active_count
            )
        return "0 предложений"
    offers_count.short_description = "Предложения"
    
    actions = ['activate_items', 'deactivate_items', 'view_item_in_catalog']
    
    def activate_items(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} товаров успешно активированы.')
    activate_items.short_description = "Активировать выбранные товары"
    
    def deactivate_items(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} товаров успешно деактивированы.')
    deactivate_items.short_description = "Деактивировать выбранные товары"
    
    def view_item_in_catalog(self, request, queryset):
        if queryset.count() == 1:
            item = queryset.first()
            return format_html(
                '<a href="/catalog/item/{}/" target="_blank" style="color: #0d6efd;">Открыть в каталоге</a>',
                item.id
            )
        else:
            self.message_user(request, 'Выберите только один товар для просмотра в каталоге.')
    view_item_in_catalog.short_description = "Открыть в каталоге"


@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ('item', 'image_preview', 'is_primary', 'order')
    list_filter = ('is_primary', 'item__vendor')
    search_fields = ('item__title', 'item__vendor__name')
    ordering = ('item', 'order')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = "Preview"


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('item', 'branch', 'current_price_display', 'original_price', 'discount_percent', 'quantity', 'status', 'end_date', 'is_expired_display')
    list_filter = ('status', 'is_active', 'item__vendor', 'item__category', 'branch', 'end_date')
    search_fields = ('item__title', 'item__vendor__name', 'branch__name')
    ordering = ('-created_at',)
    list_per_page = 25
    
    fieldsets = (
        ('Товар и филиал', {
            'fields': ('item', 'branch')
        }),
        ('Ценообразование', {
            'fields': ('original_price', 'discount_percent')
        }),
        ('Доступность', {
            'fields': ('quantity', 'start_date', 'end_date', 'is_active', 'status')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def current_price_display(self, obj):
        return f"{obj.current_price:.2f} сўм"
    current_price_display.short_description = "Текущая цена"
    
    def is_expired_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red; font-weight: bold;">Да</span>')
        return format_html('<span style="color: green; font-weight: bold;">Нет</span>')
    is_expired_display.short_description = "Истекло"
    
    actions = ['mark_as_expired', 'mark_as_available', 'mark_as_sold_out', 'activate_offers', 'deactivate_offers']
    
    def mark_as_expired(self, request, queryset):
        updated = queryset.update(status='expired')
        self.message_user(request, f'{updated} предложений отмечены как истекшие.')
    mark_as_expired.short_description = "Отметить как истекшие"
    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(status='available')
        self.message_user(request, f'{updated} предложений отмечены как доступные.')
    mark_as_available.short_description = "Отметить как доступные"
    
    def mark_as_sold_out(self, request, queryset):
        updated = queryset.update(status='sold_out')
        self.message_user(request, f'{updated} предложений отмечены как распроданные.')
    mark_as_sold_out.short_description = "Отметить как распроданные"
    
    def activate_offers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} предложений активированы.')
    activate_offers.short_description = "Активировать выбранные предложения"
    
    def deactivate_offers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} предложений деактивированы.')
    deactivate_offers.short_description = "Деактивировать выбранные предложения"
