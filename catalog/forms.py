from django import forms
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, HTML
from crispy_forms.bootstrap import FormActions
from .models import Item, Category, ItemImage, Offer, SurpriseBox, SurpriseBoxItem

User = get_user_model()


class ItemForm(forms.ModelForm):
    """Form for creating/editing items"""
    
    class Meta:
        model = Item
        fields = ['branch', 'category', 'title', 'description', 'unit', 'custom_unit', 'expiry_date', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'custom_unit': forms.TextInput(attrs={'placeholder': 'Укажите единицу измерения'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        vendor = kwargs.pop('vendor', None)
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if vendor:
            self.fields['branch'].queryset = vendor.branches.filter(is_active=True)
            self.fields['branch'].empty_label = "Выберите филиал"
        
        # Add custom units from session
        if request and hasattr(request, 'session') and 'custom_units' in request.session:
            custom_units = request.session['custom_units']
            current_choices = list(self.fields['unit'].choices)
            
            for unit in custom_units:
                unit_choice = (unit['key'], unit['display'])
                if unit_choice not in current_choices:
                    current_choices.append(unit_choice)
            
            self.fields['unit'].choices = current_choices
        
        # Make custom_unit initially hidden
        self.fields['custom_unit'].required = False
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            Row(
                Column('branch', css_class='form-group col-md-6 mb-3'),
                Column(
                    Div(
                        'category',
                        HTML('''
                            <a href="{% url 'catalog:add_category' %}" class="btn btn-outline-success btn-sm mt-2" target="_blank">
                                <i class="fas fa-plus me-1"></i>Добавить категорию
                            </a>
                        '''),
                        css_class='position-relative'
                    ),
                    css_class='form-group col-md-6 mb-3'
                ),
                css_class='form-row'
            ),
            Row(
                Column('title', css_class='form-group col-md-8 mb-3'),
                Column(
                    Div(
                        'unit',
                        HTML('''
                            <a href="{% url 'catalog:add_unit' %}" class="btn btn-outline-info btn-sm mt-2" target="_blank">
                                <i class="fas fa-plus me-1"></i>Добавить единицу
                            </a>
                        '''),
                        css_class='position-relative'
                    ),
                    css_class='form-group col-md-4 mb-3'
                ),
                css_class='form-row'
            ),
            Div(
                'custom_unit',
                css_class='mb-3',
                style='display: none;',
                id='customUnitDiv'
            ),
            'description',
            Row(
                Column('expiry_date', css_class='form-group col-md-6 mb-3'),
                Column('is_active', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            HTML('''
                <script>
                // Custom unit toggle
                function toggleCustomUnit(value) {
                    const customUnitDiv = document.getElementById('customUnitDiv');
                    if (value === 'другое') {
                        customUnitDiv.style.display = 'block';
                    } else {
                        customUnitDiv.style.display = 'none';
                    }
                }
                </script>
            '''),
            FormActions(
                Submit('submit', 'Сохранить товар', css_class='btn btn-primary btn-lg'),
                css_class='mt-3'
            )
        )
        
        # Add custom styling
        self.fields['branch'].widget.attrs.update({'class': 'form-select'})
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        self.fields['unit'].widget.attrs.update({
            'class': 'form-select',
            'onchange': 'toggleCustomUnit(this.value)'
        })
        self.fields['title'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Название товара...'
        })
        self.fields['description'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Описание товара...'
        })
        self.fields['custom_unit'].widget.attrs.update({
            'class': 'form-control'
        })
        self.fields['expiry_date'].widget.attrs.update({
            'class': 'form-control'
        })
        self.fields['expiry_date'].required = False

    def clean(self):
        cleaned_data = super().clean()
        unit = cleaned_data.get('unit')
        custom_unit = cleaned_data.get('custom_unit')
        
        # Validate custom unit
        if unit == 'другое' and not custom_unit:
            raise forms.ValidationError('Укажите единицу измерения для "Другое"')
        
        return cleaned_data


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


class CategoryForm(forms.ModelForm):
    """Form for creating new categories"""
    
    class Meta:
        model = Category
        fields = ['name', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Название категории...'}),
            'icon': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            'name',
            'icon',
            FormActions(
                Submit('submit', 'Создать категорию', css_class='btn btn-success btn-lg'),
                HTML('<a href="javascript:history.back()" class="btn btn-secondary btn-lg ms-2">Отмена</a>'),
                css_class='mt-3'
            )
        )
        
        # Add custom styling
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        category = super().save(commit=False)
        if not category.slug:
            from django.utils.text import slugify
            base_slug = slugify(category.name)
            slug = base_slug
            counter = 1
            
            # Check for existing slugs and add counter if needed
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            category.slug = slug
        if commit:
            category.save()
        return category


class UnitForm(forms.Form):
    """Form for creating new units (adds to UNIT_CHOICES)"""
    unit_key = forms.CharField(
        max_length=20,
        label="Сокращение единицы",
        help_text="Например: упак, коробка, бутылка"
    )
    unit_display = forms.CharField(
        max_length=50,
        label="Отображаемое название",
        help_text="Например: Упаковки, Коробки, Бутылки"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'unit_key',
            'unit_display',
            FormActions(
                Submit('submit', 'Добавить единицу', css_class='btn btn-info btn-lg'),
                HTML('<a href="javascript:history.back()" class="btn btn-secondary btn-lg ms-2">Отмена</a>'),
                css_class='mt-3'
            )
        )
        
        # Add custom styling
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        self.fields['unit_key'].widget.attrs.update({
            'placeholder': 'упак, коробка, бутылка...'
        })
        self.fields['unit_display'].widget.attrs.update({
            'placeholder': 'Упаковки, Коробки, Бутылки...'
        })


class OfferForm(forms.ModelForm):
    """Form for creating offers"""
    
    class Meta:
        model = Offer
        fields = ['original_price', 'discount_percent', 'quantity', 'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'original_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'discount_percent': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
            'quantity': forms.NumberInput(attrs={'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('original_price', css_class='form-group col-md-6 mb-3'),
                Column('discount_percent', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            Row(
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
            field.widget.attrs.update({'class': 'form-control'})
        
        # Add placeholders
        self.fields['original_price'].widget.attrs['placeholder'] = 'Оригинальная цена в сумах'
        self.fields['discount_percent'].widget.attrs['placeholder'] = 'Процент скидки'
        self.fields['quantity'].widget.attrs['placeholder'] = 'Количество (0 = неограниченно)'
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError('Дата окончания должна быть позже даты начала.')
        
        return cleaned_data


class SurpriseBoxForm(forms.ModelForm):
    """Form for creating/editing surprise boxes"""
    
    # Multiple select for items
    items = forms.ModelMultipleChoiceField(
        queryset=Item.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Выберите товары, которые будут включены в бокс"
    )
    
    class Meta:
        model = SurpriseBox
        fields = [
            'branch', 'title', 'description', 'box_type', 'image',
            'original_value', 'selling_price', 'total_quantity',
            'available_from', 'available_until', 'pickup_start', 'pickup_end',
            'items'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Опишите, что может быть в боксе...'}),
            'available_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'available_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'pickup_start': forms.TimeInput(attrs={'type': 'time'}),
            'pickup_end': forms.TimeInput(attrs={'type': 'time'}),
            'original_value': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'total_quantity': forms.NumberInput(attrs={'min': '1'}),
        }
    
    def __init__(self, *args, **kwargs):
        vendor = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)
        
        if vendor:
            # Filter branches and items by vendor
            self.fields['branch'].queryset = vendor.branches.filter(is_active=True)
            self.fields['items'].queryset = vendor.items.filter(is_active=True)
            self.fields['branch'].empty_label = "Выберите филиал"
        
        # Make pickup fields optional
        self.fields['pickup_start'].required = False
        self.fields['pickup_end'].required = False
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
    
    def clean(self):
        cleaned_data = super().clean()
        original_value = cleaned_data.get('original_value')
        selling_price = cleaned_data.get('selling_price')
        available_from = cleaned_data.get('available_from')
        available_until = cleaned_data.get('available_until')
        pickup_start = cleaned_data.get('pickup_start')
        pickup_end = cleaned_data.get('pickup_end')
        items = cleaned_data.get('items')
        
        # Validate pricing
        if original_value and selling_price:
            if selling_price >= original_value:
                raise forms.ValidationError('Цена продажи должна быть меньше оригинальной стоимости.')
        
        # Validate time periods
        if available_from and available_until:
            if available_until <= available_from:
                raise forms.ValidationError('Время окончания должно быть позже времени начала.')
        
        if pickup_start and pickup_end:
            if pickup_end <= pickup_start:
                raise forms.ValidationError('Время окончания самовывоза должно быть позже времени начала.')
        
        # Validate items selection
        if not items or items.count() < 2:
            raise forms.ValidationError('Выберите минимум 2 товара для создания бокса.')
        
        return cleaned_data
