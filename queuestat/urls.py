from django.urls import path
from . import views
#from .views import start_continuous_monitoring

#from .views import test_email

app_name = 'queueatats'


urlpatterns = [
    path('agent-search/', views.AgentSearchView.as_view(), name='agent_search'),
    path('agent-details/', views.AgentDetailsView.as_view(), name='agent_details'),
    #path('test-email/', test_email, name='test_email'),
    #path('monitor/', views.RealTimeMonitorView.as_view(), name='real_time_monitor'),
    
    
    path('test/', views.test_realtime_data, name='test_realtime_data'),
    
    #path('start-monitoring/', views.start_continuous_monitoring, name='start_monitoring'),

    
]