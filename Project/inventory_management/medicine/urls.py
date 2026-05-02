# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Medicine Management
    path('medicines/', views.MedicineListView.as_view(), name='medicine_list'),
    #path('medicines/<int:pk>/', views.MedicineDetailView.as_view(), name='medicine_detail'),
    path('medicines/add/', views.MedicineCreateView.as_view(), name='medicine_add'),
    #path('medicines/<int:pk>/edit/', views.MedicineUpdateView.as_view(), name='medicine_edit'),
    
    # Medicine Batch Management
    path('medicines/<int:medicine_id>/add-batch/', views.MedicineBatchCreateView.as_view(), name='add_medicine_batch'),
    
    # Inventory Reports
    path('inventory/report/', views.inventory_report, name='inventory_report'),
    
    # Sale Management
    path('sales/', views.SaleListView.as_view(), name='sale_list'),
    path('sales/add/', views.create_sale, name='create_sale'),
    path('sales/<int:pk>/', views.SaleDetailView.as_view(), name='sale_detail'),
    path('api/medicine-batch-info/', views.medicine_batch_info, name='medicine_batch_info'),
    # Alerts
    path('alerts/low-stock/', views.low_stock_alerts, name='low_stock_alerts'),
    path('alerts/expiry/', views.expiry_alerts, name='expiry_alerts'),
]