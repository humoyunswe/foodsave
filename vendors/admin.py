from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count
from .models import Vendor, Branch


class OpeningHoursWidget(forms.Textarea):
    """Custom widget for opening hours with helpful placeholder"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'rows': 10,
            'cols': 50,
            'placeholder': '''Введите часы работы в формате JSON:

{
  "monday": "09:00 - 18:00",
  "tuesday": "09:00 - 18:00", 
  "wednesday": "09:00 - 18:00",
  "thursday": "09:00 - 18:00",
  "friday": "09:00 - 18:00",
  "saturday": "10:00 - 16:00",
  "sunday": "Closed"
}

Поддерживаемые форматы:
• "09:00 - 18:00" или "09:00-18:00"
• "Closed" или "закрыто" для выходных
• Можно использовать русские названия дней'''
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

class BranchAdminForm(forms.ModelForm):
    """Custom form for Branch admin with enhanced opening_hours field"""
    
    class Meta:
        model = Branch
        fields = '__all__'
        widgets = {
            'opening_hours': OpeningHoursWidget(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['opening_hours'].help_text = '''
        <strong>Формат JSON для часов работы:</strong><br>
        <code>{"monday": "09:00 - 18:00", "tuesday": "09:00 - 18:00", ...}</code><br><br>
        <strong>Поддерживаемые форматы времени:</strong><br>
        • <code>"09:00 - 18:00"</code> - с пробелами<br>
        • <code>"09:00-18:00"</code> - без пробелов<br>
        • <code>"Closed"</code> - для выходных дней<br><br>
        <strong>Названия дней:</strong> monday, tuesday, wednesday, thursday, friday, saturday, sunday
        '''


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 1
    fields = ('name', 'address', 'phone', 'is_active')
    show_change_link = True


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('logo_display', 'name', 'type', 'owner', 'rating', 'is_active', 'branches_count', 'items_count', 'created_at')
    list_filter = ('type', 'is_active', 'rating', 'created_at')
    search_fields = ('name', 'owner__username', 'owner__email', 'description', 'phone', 'email')
    ordering = ('-created_at',)
    inlines = [BranchInline]
    list_per_page = 25
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('owner', 'name', 'type', 'description', 'logo')
        }),
        ('Контактная информация', {
            'fields': ('phone', 'email'),
            'classes': ('collapse',)
        }),
        ('Статус и рейтинг', {
            'fields': ('rating', 'is_active')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def logo_display(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />',
                obj.logo.url
            )
        return format_html(
            '<div style="width: 50px; height: 50px; background: #f8f9fa; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #6c757d;">📦</div>'
        )
    logo_display.short_description = "Логотип"
    
    def branches_count(self, obj):
        count = obj.branches.count()
        if count > 0:
            return format_html(
                '<a href="/admin/vendors/branch/?vendor__id__exact={}" style="color: #0d6efd; text-decoration: none;">{} филиалов</a>',
                obj.id, count
            )
        return "0 филиалов"
    branches_count.short_description = "Филиалы"
    
    def items_count(self, obj):
        # Подсчитываем товары через связанные филиалы
        count = 0
        for branch in obj.branches.all():
            count += branch.items.count()
        if count > 0:
            return format_html(
                '<a href="/admin/catalog/item/?branch__vendor__id__exact={}" style="color: #198754; text-decoration: none;">{} товаров</a>',
                obj.id, count
            )
        return "0 товаров"
    items_count.short_description = "Товары"
    
    actions = ['activate_vendors', 'deactivate_vendors', 'view_vendor_dashboard']
    
    def activate_vendors(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} вендоров успешно активированы.')
    activate_vendors.short_description = "Активировать выбранных вендоров"
    
    def deactivate_vendors(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} вендоров успешно деактивированы.')
    deactivate_vendors.short_description = "Деактивировать выбранных вендоров"
    
    def view_vendor_dashboard(self, request, queryset):
        if queryset.count() == 1:
            vendor = queryset.first()
            return format_html(
                '<a href="/vendors/admin/vendors/{}/" target="_blank" style="color: #0d6efd;">Открыть панель вендора</a>',
                vendor.id
            )
        else:
            self.message_user(request, 'Выберите только одного вендора для просмотра панели.')
    view_vendor_dashboard.short_description = "Открыть панель вендора"


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    form = BranchAdminForm
    list_display = ('name', 'vendor', 'address', 'phone', 'opening_status', 'is_active', 'items_count', 'created_at')
    list_filter = ('vendor__type', 'is_active', 'created_at')
    search_fields = ('name', 'vendor__name', 'address', 'phone')
    ordering = ('-created_at',)
    list_per_page = 25
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('vendor', 'name', 'address', 'phone')
        }),
        ('Расположение', {
            'fields': ('latitude', 'longitude'),
            'description': 'Координаты для расчета расстояния до клиентов'
        }),
        ('Часы работы', {
            'fields': ('opening_hours',),
            'description': 'Часы работы филиала в формате JSON'
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Временные метки', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)
    
    def opening_status(self, obj):
        """Display current opening status"""
        try:
            if obj.is_open_now():
                return format_html(
                    '<span style="color: green; font-weight: bold;">🟢 Открыто до {}</span>',
                    obj.get_closing_time()
                )
            else:
                return format_html(
                    '<span style="color: red; font-weight: bold;">🔴 {}</span>',
                    obj.get_closing_time()
                )
        except:
            return format_html('<span style="color: orange;">⚠️ Не настроено</span>')
    opening_status.short_description = "Статус работы"
    
    def items_count(self, obj):
        count = obj.items.count()
        if count > 0:
            return format_html(
                '<a href="/admin/catalog/item/?branch__id__exact={}" style="color: #198754; text-decoration: none;">{} товаров</a>',
                obj.id, count
            )
        return "0 товаров"
    items_count.short_description = "Товары"
    
    actions = ['activate_branches', 'deactivate_branches']
    
    def activate_branches(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} филиалов успешно активированы.')
    activate_branches.short_description = "Активировать выбранные филиалы"
    
    def deactivate_branches(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} филиалов успешно деактивированы.')
    deactivate_branches.short_description = "Деактивировать выбранные филиалы"
