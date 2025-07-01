from django.urls import path
from . import views

app_name = 'stotisticss'


urlpatterns = [
    
    path('form/', views.StatisticsFormView.as_view(), name='statistics_form'),
    path('total-results/', views.StatisticsResultView.as_view(), name='statistics_results'),
]