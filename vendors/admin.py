from django.contrib import admin
from django.utils.html import format_html
from django import forms
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
    list_display = ('name', 'type', 'owner', 'rating', 'is_active', 'branches_count', 'created_at')
    list_filter = ('type', 'is_active', 'rating', 'created_at')
    search_fields = ('name', 'owner__username', 'owner__email', 'description')
    ordering = ('-created_at',)
    inlines = [BranchInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'name', 'type', 'description', 'logo')
        }),
        ('Status & Rating', {
            'fields': ('rating', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def branches_count(self, obj):
        count = obj.branches.count()
        if count > 0:
            return format_html(
                '<a href="/admin/vendors/branch/?vendor__id__exact={}">{} branches</a>',
                obj.id, count
            )
        return "0 branches"
    branches_count.short_description = "Branches"
    
    actions = ['activate_vendors', 'deactivate_vendors']
    
    def activate_vendors(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} vendors were successfully activated.')
    activate_vendors.short_description = "Activate selected vendors"
    
    def deactivate_vendors(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} vendors were successfully deactivated.')
    deactivate_vendors.short_description = "Deactivate selected vendors"


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    form = BranchAdminForm
    list_display = ('name', 'vendor', 'address', 'phone', 'opening_status', 'is_active', 'items_count', 'created_at')
    list_filter = ('vendor__type', 'is_active', 'created_at')
    search_fields = ('name', 'vendor__name', 'address', 'phone')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('vendor', 'name', 'address', 'phone')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'description': 'Координаты для расчета расстояния до клиентов'
        }),
        ('Operating Hours', {
            'fields': ('opening_hours',),
            'description': 'Часы работы филиала в формате JSON'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)
    
    def opening_status(self, obj):
        """Display current opening status"""
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
    opening_status.short_description = "Статус работы"
    
    def items_count(self, obj):
        count = obj.items.count()
        if count > 0:
            return format_html(
                '<a href="/admin/catalog/item/?branch__id__exact={}">{} items</a>',
                obj.id, count
            )
        return "0 items"
    items_count.short_description = "Items"
    
    actions = ['activate_branches', 'deactivate_branches']
    
    def activate_branches(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} branches were successfully activated.')
    activate_branches.short_description = "Activate selected branches"
    
    def deactivate_branches(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} branches were successfully deactivated.')
    deactivate_branches.short_description = "Deactivate selected branches"
