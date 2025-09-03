from django import forms
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, HTML
from crispy_forms.bootstrap import FormActions
from .models import Item, Category, ItemImage, Offer

User = get_user_model()


class ItemForm(forms.ModelForm):
    """Form for creating/editing items"""
    
    class Meta:
        model = Item
        fields = ['branch', 'category', 'title', 'description', 'unit', 'tags', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'tags': forms.TextInput(attrs={'placeholder': 'Введите теги через запятую (например: халяль, вегетарианское, острое)'}),
        }
    
    def __init__(self, *args, **kwargs):
        vendor = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)
        
        if vendor:
            self.fields['branch'].queryset = vendor.branches.filter(is_active=True)
            self.fields['branch'].empty_label = "Выберите филиал"
        
        # Make tags optional and accept comma-separated input
        self.fields['tags'].required = False
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            Row(
                Column('branch', css_class='form-group col-md-6 mb-3'),
                Column('category', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('title', css_class='form-group col-md-8 mb-3'),
                Column('unit', css_class='form-group col-md-4 mb-3'),
                css_class='form-row'
            ),
            'description',
            'tags',
            'is_active',
            FormActions(
                Submit('submit', 'Сохранить товар', css_class='btn btn-primary btn-lg'),
                css_class='mt-3'
            )
        )
        
        # Add custom styling
        self.fields['branch'].widget.attrs.update({'class': 'form-select'})
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        self.fields['unit'].widget.attrs.update({'class': 'form-select'})
        self.fields['title'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Название товара...'
        })
        self.fields['description'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Описание товара...'
        })
        self.fields['tags'].widget.attrs.update({
            'class': 'form-control'
        })

    def clean_tags(self):
        value = self.cleaned_data.get('tags')
        if not value:
            return []
        # If already a list (e.g., posted as JSON), keep it
        if isinstance(value, list):
            return value
        # Accept comma-separated string
        if isinstance(value, str):
            tokens = [t.strip() for t in value.split(',') if t.strip()]
            return tokens
        return []


class ItemImageForm(forms.ModelForm):
    """Form for item images"""
    
    class Meta:
        model = ItemImage
        fields = ['image', 'is_primary', 'order']
        widgets = {
            'order': forms.NumberInput(attrs={'min': 0, 'max': 100}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].widget.attrs.update({'class': 'form-control'})
        self.fields['order'].widget.attrs.update({'class': 'form-control'})


# Create formset for multiple images
ItemImageFormSet = forms.inlineformset_factory(
    Item, ItemImage, form=ItemImageForm, extra=3, can_delete=True
)


class OfferForm(forms.ModelForm):
    """Form for creating offers"""
    
    class Meta:
        model = Offer
        fields = ['branch', 'original_price', 'discount_percent', 'quantity', 'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'original_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'discount_percent': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
            'quantity': forms.NumberInput(attrs={'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        vendor = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)
        
        if vendor:
            self.fields['branch'].queryset = vendor.branches.filter(is_active=True)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('original_price', css_class='form-group col-md-6 mb-3'),
                Column('discount_percent', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('branch', css_class='form-group col-md-6 mb-3'),
                Column('quantity', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
                Column('start_date', css_class='form-group col-md-6 mb-3'),
                Column('end_date', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            'is_active',
            FormActions(
                Submit('submit', 'Создать предложение', css_class='btn btn-success btn-lg'),
                css_class='mt-3'
            )
        )
        
        # Add custom styling
        for field_name, field in self.fields.items():
            if field_name in ['branch']:
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Add placeholders
        self.fields['original_price'].widget.attrs['placeholder'] = 'Оригинальная цена'
        self.fields['discount_percent'].widget.attrs['placeholder'] = 'Процент скидки'
        self.fields['quantity'].widget.attrs['placeholder'] = 'Количество (0 = неограниченно)'
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError('Дата окончания должна быть позже даты начала.')
        
        return cleaned_data
