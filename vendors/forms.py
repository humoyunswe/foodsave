from django import forms
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, HTML
from crispy_forms.bootstrap import FormActions
from .models import Vendor, Branch

User = get_user_model()


class OwnerForm(forms.ModelForm):
    """Form for creating new owners/users"""
    password = forms.CharField(widget=forms.PasswordInput(), label="Пароль")
    password_confirm = forms.CharField(widget=forms.PasswordInput(), label="Подтвердите пароль")
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [('vendor', 'Vendor Owner'), ('customer', 'Customer')]
        self.fields['role'].initial = 'vendor'
        
        # Add styling
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
            
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Пароли не совпадают')
        return cleaned_data
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class VendorForm(forms.ModelForm):
    """Form for creating vendors (admin only)"""
    
    class Meta:
        model = Vendor
        fields = ['owner', 'type', 'name', 'description', 'logo', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            Row(
                Column('owner', css_class='form-group col-md-8 mb-3'),
                Column(
                    HTML('''
                        <div class="form-group">
                            <label class="form-label">&nbsp;</label>
                            <button type="button" class="btn btn-outline-success btn-sm w-100" 
                                    data-bs-toggle="modal" data-bs-target="#addOwnerModal">
                                <i class="fas fa-user-plus me-1"></i>Добавить владельца
                            </button>
                        </div>
                    '''),
                    css_class='col-md-4 mb-3'
                ),
                css_class='form-row'
            ),
            'type',
            'name',
            'description',
            'logo',
            'is_active',
            FormActions(
                Submit('submit', 'Создать vendor', css_class='btn btn-primary btn-lg'),
                css_class='mt-3'
            )
        )
        
        # Add custom styling
        self.fields['owner'].widget.attrs.update({'class': 'form-select'})
        self.fields['type'].widget.attrs.update({'class': 'form-select'})
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Название заведения...'
        })
        self.fields['description'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Описание заведения...'
        })
        self.fields['logo'].widget.attrs.update({'class': 'form-control'})
        
        # Set queryset for owner field to show all users
        self.fields['owner'].queryset = User.objects.all()
        self.fields['owner'].empty_label = "Выберите владельца"


class BranchForm(forms.ModelForm):
    """Form for creating branches"""
    
    # Days of week choices
    DAYS_CHOICES = [
        ('monday', 'Понедельник'),
        ('tuesday', 'Вторник'),
        ('wednesday', 'Среда'),
        ('thursday', 'Четверг'),
        ('friday', 'Пятница'),
        ('saturday', 'Суббота'),
        ('sunday', 'Воскресенье'),
    ]
    
    # Time choices (30-minute intervals)
    TIME_CHOICES = [(f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}") 
                    for h in range(24) for m in [0, 30]]
    
    class Meta:
        model = Branch
        fields = ['name', 'address', 'latitude', 'longitude', 'phone', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'name': 'Название филиала',
            'address': 'Адрес филиала', 
            'latitude': 'Широта',
            'longitude': 'Долгота',
            'phone': 'Телефон',
            'is_active': 'Филиал активен'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'premium-form'
        self.helper.layout = Layout(
            Div(
                # Left Column
                Div(
                    'name',
                    HTML('''
                        <div class="input-group phone-group">
                            <label for="id_phone" class="input-label">Телефон</label>
                            <div class="phone-input-wrapper">
                                <div class="country-flag">
                                    <img src="data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 513 342'%3e%3cpath fill='%2300afca' d='M0 0h513v114H0z'/%3e%3cpath fill='%23fff' d='M0 114h513v114H0z'/%3e%3cpath fill='%23ce1126' d='M0 228h513v114H0z'/%3e%3ccircle cx='128.5' cy='57' r='34.2' fill='%23fff'/%3e%3ccircle cx='136.8' cy='57' r='27.4' fill='%2300afca'/%3e%3cpath fill='%23fff' d='m128.5 30.4 4.6 14.1h14.8l-12 8.7 4.6 14.1-12-8.7-12 8.7 4.6-14.1-12-8.7h14.8z'/%3e%3c/svg%3e" alt="UZ" class="flag-icon">
                                    <span class="country-code">+998</span>
                                </div>
                    '''),
                    'phone',
                    HTML('</div></div>'),
                    'address',
                    Div(
                        Row(
                            Column('latitude', css_class='col-6'),
                            Column('longitude', css_class='col-6'),
                        ),
                        css_class='coordinates-group'
                    ),
                    Div(
                        'is_active',
                        css_class='toggle-group'
                    ),
                    css_class='form-column'
                ),
                # Right Column  
                Div(
                    HTML('''
                        <div class="map-section">
                            <label class="input-label">Местоположение на карте</label>
                            <div class="map-container">
                                <div id="map"></div>
                            </div>
                            <p class="map-hint">Кликните на карте для выбора точного местоположения</p>
                        </div>
                        
                        <div class="map-controls">
                            <button type="button" class="control-btn" onclick="getCurrentLocation()">
                                Моё местоположение
                            </button>
                            <button type="button" class="control-btn" onclick="searchByAddress()">
                                Найти по адресу
                            </button>
                            <button type="button" class="control-btn" onclick="centerMap()">
                                Центрировать
                            </button>
                        </div>
                    '''),
                    css_class='form-column'
                ),
                css_class='form-grid'
            )
        )
        
        # Add custom styling
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '',
        })
        self.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '',
        })
        self.fields['latitude'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '',
            'step': 'any',
        })
        self.fields['longitude'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '',
            'step': 'any',
        })
        self.fields['phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'xx xxx xx xx',
            'pattern': '[0-9]{2} [0-9]{3} [0-9]{2} [0-9]{2}',
            'title': 'Формат: 90 123 45 67',
        })


class AssignVendorRoleForm(forms.Form):
    """Staff form to assign vendor role to an existing user"""
    user = forms.ModelChoiceField(queryset=User.objects.all(), label="Пользователь")
    make_staff = forms.BooleanField(required=False, initial=False, label="Сделать сотрудником (staff)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].widget.attrs.update({'class': 'form-select'})
        self.fields['make_staff'].widget.attrs.update({'class': 'form-check-input'})

    def save(self):
        user = self.cleaned_data['user']
        make_staff = self.cleaned_data.get('make_staff', False)
        user.role = 'vendor'
        if make_staff:
            user.is_staff = True
        user.save()
        return user
