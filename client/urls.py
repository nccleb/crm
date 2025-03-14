from django.urls import path

from . import views

app_name = 'clients'
urlpatterns = [
    
    path('', views.clients_list, name='list'),
    path('<int:pk>/', views.clients_detail, name='detail'),
    path('<int:pk>/delete', views.clients_delete, name='delete'),
    path('edit/<int:pk>', views.clients_edit, name='edit'),
    
    path('add/', views.clients_add, name='add'),
]