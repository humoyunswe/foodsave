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
    
    class Meta:
        model = Branch
        fields = ['name', 'address', 'latitude', 'longitude', 'phone', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'name',
            'address',
            Row(
                Column('latitude', css_class='form-group col-md-6 mb-3'),
                Column('longitude', css_class='form-group col-md-6 mb-3'),
                css_class='form-row'
            ),
            'phone',
            'is_active',
            FormActions(
                Submit('submit', 'Создать филиал', css_class='btn btn-primary btn-lg'),
                css_class='mt-3'
            )
        )
        
        # Add custom styling
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Название филиала...',
            'required': True
        })
        self.fields['address'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Адрес филиала...',
            'required': True
        })
        self.fields['latitude'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Широта',
            'step': 'any',
            'required': True
        })
        self.fields['longitude'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Долгота',
            'step': 'any',
            'required': True
        })
        self.fields['phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '+7 (xxx) xxx-xx-xx',
            'required': True
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
