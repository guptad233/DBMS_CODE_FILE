from django.contrib import admin
from .models import (
    Medicine, Sale, SaleItem,
 PurchaseOrder, PurchaseOrderItem,MedicineUser
)

admin.site.register(MedicineUser)


admin.site.register(Medicine)

admin.site.register(Sale)
admin.site.register(SaleItem)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)