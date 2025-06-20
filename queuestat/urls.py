from django.urls import path
from . import views

app_name = 'queueatats'


urlpatterns = [
    path('agent-search/', views.AgentSearchView.as_view(), name='agent_search'),
    path('agent-details/', views.AgentDetailsView.as_view(), name='agent_details'),
    
]