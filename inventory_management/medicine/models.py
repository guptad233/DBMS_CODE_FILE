# models.py
from django.db import models,transaction
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)



class MedicineUser(AbstractUser):
    """Custom User model that uses email as the unique identifier instead of username."""
    username = None
    email = models.EmailField('Email Address', unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class Medicine(models.Model):
    name = models.CharField(max_length=100)
    generic_name = models.CharField(max_length=100, blank=True, null=True)
    category = models.TextField(max_length=50)
    description = models.TextField(blank=True, null=True)
    minimum_stock = models.PositiveIntegerField(default=10)
    supplier = models.TextField(max_length=50)
    user = models.ForeignKey(MedicineUser, on_delete=models.CASCADE, related_name='medicines')

    def __str__(self):
        return self.name

    @property
    def current_stock(self):
        return sum(batch.current_quantity for batch in self.batches.filter(is_active=True))

    @property
    def is_low_stock(self):
        return self.current_stock < self.minimum_stock

    @property
    def expired_batches(self):
        today = timezone.now().date()
        return self.batches.filter(expiry_date__lt=today, is_active=True)

    @property
    def soon_to_expire_batches(self):
        today = timezone.now().date()
        thirty_days_later = today + timedelta(days=30)
        return self.batches.filter(
            expiry_date__gte=today,
            expiry_date__lte=thirty_days_later,
            is_active=True
        )


class MedicineBatch(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='batches')
    user = models.ForeignKey(MedicineUser, on_delete=models.CASCADE, related_name='medicine_batches')
    batch_number = models.CharField(max_length=50)
    manufacturing_date = models.DateField()
    expiry_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_received = models.PositiveIntegerField()
    current_quantity = models.PositiveIntegerField()
    received_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.medicine.name} - {self.batch_number}"

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def days_to_expiry(self):
        today = timezone.now().date()
        if self.expiry_date < today:
            return -1 * (today - self.expiry_date).days
        return (self.expiry_date - today).days

    class Meta:
        verbose_name_plural = "Medicine Batches"


class Sale(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True)
    sale_date = models.DateTimeField(default=timezone.now)
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    user = models.ForeignKey(MedicineUser, on_delete=models.CASCADE, related_name='sales')

    def clean(self):
        """Validate the sale."""
        if not self.invoice_number:
            raise ValidationError({'invoice_number': 'Invoice number is required.'})
        
        # Check if the invoice number is unique
        existing_sale = Sale.objects.filter(invoice_number=self.invoice_number)
        if self.pk:
            existing_sale = existing_sale.exclude(pk=self.pk)
        if existing_sale.exists():
            raise ValidationError({'invoice_number': 'This invoice number is already in use.'})
    
    def save(self, *args, **kwargs):
        """Save the sale and update the stock."""
        # First, save the Sale object to generate a primary key
        if not self.pk:  # Only save if it's a new instance (without pk)
            super().save(*args, **kwargs)

        # Calculate the total_amount after the Sale instance has a primary key

        # Save again with the calculated total_amount
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Sale #{self.invoice_number}"
    
    
class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    medicine_batch = models.ForeignKey(MedicineBatch, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(MedicineUser, on_delete=models.CASCADE, related_name='sale_items')

    @property
    def subtotal(self):
        """Calculate the subtotal for this item."""
        return self.quantity * self.price
    
    def clean(self):
    
     if not self.medicine_batch_id:
        raise ValidationError({'medicine_batch': 'Medicine batch is required.'})

     if self.quantity <= 0:
        raise ValidationError({'quantity': 'Quantity must be greater than zero.'})

     if self.price <= 0:
        raise ValidationError({'price': 'Price must be greater than zero.'})

    # Check if we have enough stock
     if self.medicine_batch and self.medicine_batch.current_quantity < self.quantity:
        raise ValidationError({
            'quantity': f'Not enough stock. Available: {self.medicine_batch.current_quantity}'
        })

    
    def save(self, *args, **kwargs):
        # Check if we should skip inventory updates (when handled by the view)
        skip_inventory_update = kwargs.pop('skip_inventory_update', False)
        
        # Run validation
        self.clean()
        
        # Calculate quantity difference for existing records
        old_quantity = 0
        if self.pk:
            try:
                old_item = SaleItem.objects.get(pk=self.pk)
                old_quantity = old_item.quantity
            except SaleItem.DoesNotExist:
                pass
        
        with transaction.atomic():
            # Save the sale item
            super().save(*args, **kwargs)
            
            # Skip inventory updates if requested
            if not skip_inventory_update and self.medicine_batch:
                # Calculate the change in quantity
                qty_change = self.quantity - old_quantity
                
                # Update the batch stock
                batch = self.medicine_batch
                batch.current_quantity -= qty_change
                batch.save()
    
    def delete(self, *args, **kwargs):
    
     with transaction.atomic():
        batch = self.medicine_batch
        batch.current_quantity += self.quantity
        batch.save()
        super().delete(*args, **kwargs)

    
    def __str__(self):
        return f"{self.medicine_batch_id} x {self.quantity}"



class PurchaseOrder(models.Model):
    
    order_number = models.CharField(max_length=50, unique=True)
    supplier = models.TextField(max_length=50)
    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    user = models.ForeignKey(MedicineUser, on_delete=models.CASCADE, related_name='purchase_orders')

    def __str__(self):
        return self.order_number


class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    user = models.ForeignKey(MedicineUser, on_delete=models.CASCADE, related_name='purchase_order_items')

    def __str__(self):
        return f"{self.order.order_number} - {self.medicine.name}"