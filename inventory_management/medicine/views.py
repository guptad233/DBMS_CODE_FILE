# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, F, Q
from django.contrib import messages
from django.http import JsonResponse

from datetime import timedelta

from .models import (
    Medicine, Sale, SaleItem, 
     PurchaseOrder, PurchaseOrderItem,MedicineBatch
)
from .forms import (
    MedicineForm, SaleForm, SaleItemFormSet,
      PurchaseOrderForm, PurchaseOrderItemFormSet,MedicineBatchForm
)

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import LoginForm, CustomUserCreationForm

def login_view(request):
    # if request.user.is_authenticated:
    #     return redirect('dashboard')  # Redirect to some dashboard/homepage

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Successfully logged in.")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, 'medicine/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

def register_view(request):
    # if request.user.is_authenticated:
    #     return redirect('dashboard')

    form = CustomUserCreationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")

    return render(request, 'medicine/register.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')


#Dashboard View
from django.db.models import F, Sum
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.shortcuts import render
from datetime import timedelta

from .models import Medicine, MedicineBatch, Sale

@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()
    thirty_days_later = today + timedelta(days=30)
    first_day_of_month = today.replace(day=1)

    # Fetch list of low stock medicines
    all_medicines = Medicine.objects.filter(user=user).prefetch_related('batches')
    low_stock_medicines = [med for med in all_medicines if med.is_low_stock]
    low_stock_count = len(low_stock_medicines)


    # Count of low stock medicines
    

    # Count of expired medicine batches
    expired_batches = MedicineBatch.objects.filter(
    medicine__user=user,
    expiry_date__lt=today,
    is_active=True
).count()

    # Count of soon-to-expire medicine batches
    expiring_soon_count = MedicineBatch.objects.filter(
        user=user,
        expiry_date__gte=today,
        expiry_date__lte=thirty_days_later,
        is_active=True
    ).count()

    # Recent sales by user
    recent_sales = Sale.objects.filter(user=user).order_by('-sale_date')[:5]

    # Total monthly sales by user
    monthly_sales = Sale.objects.filter(
        user=user,
        sale_date__gte=first_day_of_month
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    context = {
        'low_stock_count': low_stock_count,
        'expired_batches': expired_batches,
        'expiring_soon_count': expiring_soon_count,
        'recent_sales': recent_sales,
        'monthly_sales': monthly_sales,
        'low_stock_medicines': low_stock_medicines,
    }
    return render(request, 'medicine/dashboard.html', context)


# @login_required
# def dashboard(request):
#     # Get the logged-in user
#     user = request.user

#     # Count of low stock medicines for the logged-in user
#     low_stock_count = Medicine.objects.filter(
#         user=user,  # Only medicines related to the logged-in user
#         minimum_stock__gt=F('batches__current_quantity')
#     ).distinct().count()

#     # Count of expired medicines for the logged-in user
#     today = timezone.now().date()
#     expired_batches = PurchaseOrderItem.objects.filter(
#         medicine__user=user,  # Only medicine batches related to the logged-in user
#         expiry_date__lt=today,
#         is_active=True
#     ).count()

#     # Count of medicines expiring in 30 days for the logged-in user
#     thirty_days_later = today + timedelta(days=30)
#     expiring_soon_count = PurchaseOrderItem.objects.filter(
#         medicine__user=user,  # Only medicine batches related to the logged-in user
#         expiry_date__gte=today,
#         expiry_date__lte=thirty_days_later,
#         is_active=True
#     ).count()

#     # Recent sales for the logged-in user
#     recent_sales = Sale.objects.filter(
#         user=user  # Only sales made by the logged-in user
#     ).order_by('-sale_date')[:5]

#     # Total sales amount for the current month for the logged-in user
#     first_day_of_month = today.replace(day=1)
#     monthly_sales = Sale.objects.filter(
#         user=user,  # Only sales made by the logged-in user
#         sale_date__gte=first_day_of_month
#     ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

#     context = {
#         'low_stock_count': low_stock_count,
#         'expired_batches': expired_batches,
#         'expiring_soon_count': expiring_soon_count,
#         'recent_sales': recent_sales,
#         'monthly_sales': monthly_sales,
#     }

#     return render(request, 'medicine/dashboard.html', context)



# Medicine Views
class MedicineListView(LoginRequiredMixin, ListView):
    model = Medicine
    template_name = 'medicine/medicine_list.html'
    context_object_name = 'medicines'
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user)
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(generic_name__icontains=search_query)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context

class MedicineBatchCreateView(LoginRequiredMixin, CreateView):
    model = MedicineBatch
    form_class = MedicineBatchForm
    template_name = 'medicine/medicine_batch_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        medicine_id = self.kwargs.get('medicine_id')
        if medicine_id:
            initial['medicine'] = medicine_id
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        medicine_id = self.kwargs.get('medicine_id')
        if medicine_id:
            context['medicine'] = get_object_or_404(Medicine, pk=medicine_id)
        return context
    
    def get_success_url(self):
        return reverse_lazy('medicine_list')
    
    def form_valid(self, form):
        form.instance.current_quantity = form.instance.quantity_received
        form.instance.user = self.request.user  # Assign the current user
        messages.success(self.request, 'Medicine batch added successfully.')
        return super().form_valid(form)


class MedicineDetailView(LoginRequiredMixin, DetailView):
    model = Medicine
    template_name = 'medicine/medicine_detail.html'
    context_object_name = 'medicine'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        medicine = self.object
        context['active_batches'] = medicine.batches.filter(is_active=True).order_by('expiry_date')
        context['expired_batches'] = medicine.expired_batches
        context['soon_to_expire_batches'] = medicine.soon_to_expire_batches
        return context


class MedicineCreateView(LoginRequiredMixin, CreateView):
    model = Medicine
    form_class = MedicineForm
    template_name = 'medicine/medicine_form.html'
    success_url = reverse_lazy('medicine_list')

    def form_valid(self, form):
        # Check if the medicine already exists for the current user
        medicine_name = form.cleaned_data['name']  # Adjust this based on the field you want to check
        if Medicine.objects.filter(user=self.request.user, name=medicine_name).exists():
            messages.error(self.request, 'This medicine is already added by you.')
            return redirect('medicine_add')  # Redirect to the medicine create page (or another appropriate page)

        # Set the user for the new medicine instance
        form.instance.user = self.request.user
        messages.success(self.request, 'Medicine added successfully.')
        return super().form_valid(form)

class MedicineUpdateView(LoginRequiredMixin, UpdateView):
    model = Medicine
    form_class = MedicineForm
    template_name = 'medicine/medicine_form.html'

    def get_success_url(self):
        return reverse_lazy('medicine_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.user = self.request.user  # Ensure user is set (optional here if unchanged)
        messages.success(self.request, 'Medicine updated successfully.')
        return super().form_valid(form)


# Medicine Batch Views
# class MedicineBatchCreateView(LoginRequiredMixin, CreateView):
#     model = MedicineBatch
#     form_class = MedicineBatchForm
#     template_name = 'medicine/medicine_batch_form.html'
    
#     def get_initial(self):
#         initial = super().get_initial()
#         medicine_id = self.kwargs.get('medicine_id')
#         if medicine_id:
#             initial['medicine'] = medicine_id
#         return initial
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         medicine_id = self.kwargs.get('medicine_id')
#         if medicine_id:
#             context['medicine'] = get_object_or_404(Medicine, pk=medicine_id)
#         return context
    
#     def get_success_url(self):
#         return reverse_lazy('medicine_detail', kwargs={'pk': self.object.medicine.pk})
    
#     def form_valid(self, form):
#         form.instance.current_quantity = form.instance.quantity_received
#         messages.success(self.request, 'Medicine batch added successfully.')
#         return super().form_valid(form)


# Inventory Reports
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from .models import Medicine

@login_required
def inventory_report(request):
    medicines = Medicine.objects.filter(user=request.user)
    

    # Remove category filter logic
    # Remove supplier references (if any)

    low_stock = request.GET.get('low_stock')
    expiry_filter = request.GET.get('expiry')

    if low_stock:
        medicines = [m for m in medicines if m.is_low_stock]

    today = timezone.now().date()
    today = timezone.now().date()
    soon_expiry_date = today + timedelta(days=30)

    if expiry_filter == 'expired':
        medicines = [m for m in medicines if m.expired_batches.exists()]
    elif expiry_filter == 'soon':
        medicines = [m for m in medicines if m.soon_to_expire_batches.exists()]

    context = {
        'medicines': medicines,
        'low_stock_filter': low_stock,
        'expiry_filter': expiry_filter,
        'today': today,
        'soon_expiry_date': soon_expiry_date,
    }
    
    return render(request, 'medicine/inventory_report.html', context)


# Sale Views
# Replace your existing create_sale view with this improved version

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from .models import Sale, SaleItem, MedicineBatch
from .forms import SaleForm, SaleItemFormSet


# Add this validation to ensure medicine_batch is selected before form submission

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .forms import SaleForm, SaleItemFormSet
from .models import Sale

@transaction.atomic
def create_sale(request):
    """View for creating a new sale with proper validation."""
    if request.method == 'POST':
        print(request.POST)  # Keep for debugging
        form = SaleForm(request.POST)

        if form.is_valid():
            sale = form.save(commit=False)
            sale.user = request.user
            sale.save()

            # Initialize total amount here
            total_amount = 0

            # Bind formset to request.POST and unsaved sale
            formset = SaleItemFormSet(request.POST, instance=sale, request=request)

            # Apply medicine batch filtering to each form
            today = timezone.now().date()
            medicine_batches = MedicineBatch.objects.filter(
                user=request.user,
                expiry_date__gte=today,
                current_quantity__gt=0,
                is_active=True
            )
            
            for form in formset.forms:
                form.fields['medicine_batch'].queryset = medicine_batches

            if formset.is_valid():
                has_empty_medicine_batch = False
                
                # Debug: Print total forms in formset
                print(f"Total forms: {len(formset.forms)}")
                
                for i, form_data in enumerate(formset.forms):
                    # Debug: Print form data for diagnosis
                    print(f"Form {i} data: {form_data.cleaned_data}")
                    
                    # Skip deleted forms
                    if form_data.cleaned_data.get('DELETE', False):
                        print(f"Form {i} marked for deletion, skipping")
                        continue

                    if not form_data.cleaned_data.get('medicine_batch') and (
                        form_data.cleaned_data.get('quantity') or form_data.cleaned_data.get('price')): 
                        form_data.add_error('medicine_batch', 'This field is required.')
                        messages.error(request, f"Item #{i+1}: Medicine batch is required but was not selected.")
                        has_empty_medicine_batch = True

                    # Calculate total_amount for each item with better validation
                    medicine_batch = form_data.cleaned_data.get('medicine_batch')
                    quantity = form_data.cleaned_data.get('quantity')
                    price = form_data.cleaned_data.get('price')
                    
                    if medicine_batch and quantity and price:
                        item_total = quantity * price
                        total_amount += item_total
                        print(f"Adding item total: {item_total}, running total: {total_amount}")

                if has_empty_medicine_batch:
                    pass  # Skip saving
                else:
                    try:
                        # Debug: Print final total before saving
                        print(f"Final total amount: {total_amount}")
                        
                        # Update sale total
                        sale.total_amount = total_amount
                        sale.save()

                        sale_items = formset.save(commit=False)

                        for sale_item in sale_items:
                            sale_item.user = request.user

                            if not sale_item.medicine_batch_id:
                                raise ValidationError("A medicine batch must be selected for each item.")

                            batch = sale_item.medicine_batch

                            if batch.current_quantity < sale_item.quantity:
                                raise ValidationError(f"Not enough stock for {batch}. Available: {batch.current_quantity}")

                            # Deduct stock and save
                            batch.current_quantity -= sale_item.quantity
                            batch.save()
                            
                            # Skip the automatic inventory update in the SaleItem.save method
                            sale_item.save(skip_inventory_update=True)

                        # Handle deletions
                        for obj in formset.deleted_objects:
                            if obj.medicine_batch_id:
                                batch = obj.medicine_batch
                                batch.current_quantity += obj.quantity
                                batch.save()
                            obj.delete()

                        messages.success(request, 'Sale recorded successfully!')
                        return redirect('sale_list')

                    except ValidationError as e:
                        transaction.set_rollback(True)
                        messages.error(request, str(e))

            else:
                for i, form_errors in enumerate(formset.errors):
                    for field, error in form_errors.items():
                        messages.error(request, f"Item #{i+1} - {field}: {error}")
                for error in formset.non_form_errors():
                    messages.error(request, error)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        sale_instance = Sale()
        form = SaleForm(initial={'sale_date': timezone.now()})
        formset = SaleItemFormSet(instance=sale_instance, request=request)
        
        # Apply medicine batch filtering for GET requests too
        today = timezone.now().date()
        medicine_batches = MedicineBatch.objects.filter(
            user=request.user,
            expiry_date__gte=today,
            current_quantity__gt=0,
            is_active=True
        )
        
        for form in formset.forms:
            form.fields['medicine_batch'].queryset = medicine_batches

    return render(request, 'medicine/sale_form.html', {
        'form': form,
        'formset': formset,
    })

def medicine_batch_info(request):
    """API endpoint to get information about active medicine batches."""
    today = timezone.now().date()
    batches = MedicineBatch.objects.filter(
        expiry_date__gte=today,
        current_quantity__gt=0,
        is_active=True
    ).values('id', 'medicine__name', 'batch_number', 'current_quantity', 'retail_price')
    
    # Format the data for frontend use
    batch_data = []
    for batch in batches:
        batch_data.append({
            'id': batch['id'],
            'name': f"{batch['medicine__name']} (Batch: {batch['batch_number']})",
            'current_quantity': batch['current_quantity'],
            'retail_price': float(batch['retail_price'])
        })
    
    return JsonResponse(batch_data, safe=False)

# def create_sale(request):
#     if request.method == 'POST':
#         form = SaleForm(request.POST)
#         formset = SaleItemFormSet(request.POST)
        
#         if form.is_valid() and formset.is_valid():
#             sale = form.save(commit=False)
#             sale.user = request.user  # Associate with current user
            
#             total_amount = 0
#             for sale_item_form in formset:
#                 if sale_item_form.cleaned_data and not sale_item_form.cleaned_data.get('DELETE', False):
#                     quantity = sale_item_form.cleaned_data.get('quantity')
#                     price = sale_item_form.cleaned_data.get('price')
#                     total_amount += quantity * price
            
#             sale.total_amount = total_amount
#             sale.save()
            
#             instances = formset.save(commit=False)
#             for instance in instances:
#                 instance.sale = sale
#                 instance.save()
            
#             messages.success(request, 'Sale recorded successfully.')
#             return redirect('sale_detail', pk=sale.pk)
#     else:
#         form = SaleForm()
#         formset = SaleItemFormSet()
    
#     context = {
#         'form': form,
#         'formset': formset,
#     }
#     return render(request, 'medicine/sale_form.html', context)


class SaleDetailView(LoginRequiredMixin, DetailView):
    model = Sale
    template_name = 'pharmacy/sale_detail.html'
    context_object_name = 'sale'

    def get_queryset(self):
        return Sale.objects.filter(user=self.request.user)


class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = 'pharmacy/sale_list.html'
    context_object_name = 'sales'
    ordering = ['-sale_date']
    paginate_by = 10

    def get_queryset(self):
        return Sale.objects.filter(user=self.request.user).order_by('-sale_date')



# Low Stock and Expiry Alerts
@login_required
def low_stock_alerts(request):
    medicines = Medicine.objects.filter(user=request.user)
    low_stock_medicines = [medicine for medicine in medicines if medicine.is_low_stock]
    
    context = {
        'low_stock_medicines': low_stock_medicines,
    }
    return render(request, 'medicine/low_stock_alerts.html', context)


@login_required
def expiry_alerts(request):
    today = timezone.now().date()
    thirty_days_later = today + timedelta(days=30)

    user_medicine_ids = Medicine.objects.filter(user=request.user).values_list('id', flat=True)

    expired_batches = MedicineBatch.objects.filter(
        expiry_date__lt=today,
        is_active=True,
        medicine_id__in=user_medicine_ids
    ).order_by('expiry_date')

    expiring_soon_batches = MedicineBatch.objects.filter(
        expiry_date__gte=today,
        expiry_date__lte=thirty_days_later,
        is_active=True,
        medicine_id__in=user_medicine_ids
    ).order_by('expiry_date')

    context = {
        'expired_batches': expired_batches,
        'expiring_soon_batches': expiring_soon_batches,
    }
    return render(request, 'medicine/expiry_alerts.html', context)
