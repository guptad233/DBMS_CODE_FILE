from django import forms
from django.forms import inlineformset_factory
from .models import (
    Medicine, Sale, SaleItem, 
    PurchaseOrder, PurchaseOrderItem, MedicineUser,MedicineBatch
)
from django.db import transaction
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db.models import Subquery, OuterRef, Sum, Q
from django.utils import timezone
from django.core.exceptions import ValidationError

from django.forms.models import BaseInlineFormSet

from django.forms.models import BaseInlineFormSet

from django.forms.models import BaseInlineFormSet

class BaseSaleItemFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)  # Grab the request object safely
        super().__init__(*args, **kwargs)
    
    def _construct_form(self, i, **kwargs):
        # This is the key change - pass request to the form kwargs
        kwargs['request'] = self.request
        return super()._construct_form(i, **kwargs)

class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
            'id': 'id_username'
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'id_password'
        })
    )


class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    )

    class Meta:
        model = MedicineUser
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if MedicineUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['name', 'generic_name', 'category', 'description', 'minimum_stock', 'supplier']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class MedicineBatchForm(forms.ModelForm):
    class Meta:
        model = MedicineBatch
        fields = [
            'medicine', 'batch_number', 'manufacturing_date', 
            'expiry_date', 'purchase_price', 'selling_price', 
            'quantity_received', 'received_date'
        ]
        widgets = {
            'manufacturing_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'received_date': forms.DateInput(attrs={'type': 'date'}),
        }


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['invoice_number', 'customer_name', 'customer_phone', 'sale_date']
        widgets = {
            'sale_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['medicine_batch', 'quantity', 'price']
        widgets = {
            'medicine_batch': forms.Select(attrs={'class': 'form-control item-medicine_batch', 'required': 'required'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control item-quantity', 'min': '1', 'required': 'required'}),
            'price': forms.NumberInput(attrs={'class': 'form-control item-price', 'step': '0.01', 'min': '0.01', 'required': 'required'}),
        }
    
    def __init__(self, *args, **kwargs):
        # We can get request from kwargs (from _construct_form) 
        # or it might be set as an attribute later (from add_fields)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Note: filtering is now handled directly in the view, but we'll leave this as a backup
        if self.request:
            today = timezone.now().date()
            self.fields['medicine_batch'].queryset = MedicineBatch.objects.filter(
                user=self.request.user,
                expiry_date__gte=today,
                current_quantity__gt=0,
                is_active=True
            )
        
        # Make sure the 'medicine_batch' field is required
        self.fields['medicine_batch'].required = True
        self.fields['medicine_batch'].label_from_instance = lambda obj: f"{obj.medicine.name} (Batch: {obj.batch_number}) - Stock: {obj.current_quantity}"
    
    def clean_medicine_batch(self):
        """Explicit validation for medicine_batch field."""
        medicine_batch = self.cleaned_data.get('medicine_batch')
        if not medicine_batch:
            raise forms.ValidationError("Medicine batch is required.")
        return medicine_batch
    
    def clean(self):
        cleaned_data = super().clean()
        medicine_batch = cleaned_data.get('medicine_batch')
        quantity = cleaned_data.get('quantity')
        
        if not medicine_batch:
            raise forms.ValidationError({'medicine_batch': 'Medicine batch is required.'})
            
        if not quantity or quantity <= 0:
            raise forms.ValidationError({'quantity': 'Quantity must be greater than zero.'})
            
        if quantity > medicine_batch.current_quantity:
            raise forms.ValidationError({'quantity': f"Requested quantity ({quantity}) exceeds available stock ({medicine_batch.current_quantity})"})
        
        return cleaned_data    
    
# Create a formset for sale items with improved validation
SaleItemFormSet = inlineformset_factory(
    Sale, 
    SaleItem,
    form=SaleItemForm,
    formset=BaseSaleItemFormSet,
    extra=1,
    can_delete=True
)



class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['order_number', 'supplier', 'order_date', 'expected_delivery_date', 'notes']
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make required fields more obvious
        for field_name in ['order_number', 'supplier', 'order_date']:
            self.fields[field_name].required = True
            self.fields[field_name].widget.attrs['required'] = True
        
        # Supplier is now a text field (input)
        self.fields['supplier'].widget = forms.TextInput(attrs={
            'placeholder': 'Enter supplier name',
            'required': True
        })


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['medicine', 'quantity', 'unit_price']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get medicines with low stock
        low_stock_qs = Medicine.objects.filter(
            minimum_stock__gt=Subquery(
                MedicineBatch.objects.filter(
                    medicine=OuterRef('pk'),
                    is_active=True
                ).values('medicine').annotate(
                    total=Sum('current_quantity')
                ).values('total')[:1]
            )
        )
        
        # Get all medicines excluding low stock ones
        queryset = Medicine.objects.all()
        
        # Combine low stock medicines and others using the | operator
        self.fields['medicine'].queryset = low_stock_qs | queryset.exclude(pk__in=low_stock_qs.values_list('pk', flat=True))
        
        # Make required fields more obvious
        self.fields['medicine'].required = True
        self.fields['quantity'].required = True
        self.fields['medicine'].widget.attrs['required'] = True
        self.fields['quantity'].widget.attrs['required'] = True
        self.fields['quantity'].widget.attrs['min'] = 1


# Create a formset for purchase order items
PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder, 
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
