from django.urls import path, include

from . import views

app_name = 'leads'

urlpatterns = [
    path('', views.LeadListView.as_view(), name='list'),
    path('<int:pk>/', views.LeadDetailView.as_view(), name='detail'),
    path('<int:pk>/delete/', views.LeadDeleteView.as_view(), name='delete'),
    path('<int:pk>/edit/', views.LeadUpdateView.as_view(), name='edit'),
    path('<int:pk>/convert/', views.ConvertToClientView.as_view(), name='convert'),
    path('<int:pk>/add-comment/', views.AddCommentView.as_view(), name='add_comment'),
    path('<int:pk>/add-file/', views.AddFileView.as_view(), name='add_file'),
    #path('add/', views.LeadCreateView.as_view(), name='add'),
    path('', views.leads_list, name='leads_list'),
    
    path('<int:pk>/', views.leads_detail, name='leads_detail'),
    #path('<int:pk>/delete/', views.leads_delete, name='leads_delete'),
    #path('<int:pk>/', views.leads_detail, name='leads_detail'),
    # path('add_lead/',views.add_lead, name='add_lead' ),
   
    
]
   