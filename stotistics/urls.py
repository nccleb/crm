from django.urls import path
from . import views

app_name = 'stotisticss'


urlpatterns = [
    
    path('form/', views.StatisticsFormView.as_view(), name='statistics_form'),
    path('total-results/', views.StatisticsResultView.as_view(), name='statistics_results'),
    path('formqueue/', views.StatisticsQueueFormView, name='statistics_Queue_form'),
    path('total-Queue-results/', views.StatisticsQueueResultView.as_view(), name='statistics_queue_results'),
    path('formagent/', views.StatisticsAgentFormView, name='statistics_Agent_form'),
    path('total-agent-results/', views.StatisticsAgentResultView.as_view(), name='statistics_agent_results'),
]