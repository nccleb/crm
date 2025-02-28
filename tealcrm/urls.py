from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views
from django.urls import include, path
from core.views import UserLogoutView, about, index
from dashboard.views import dashboard
from userprofile.views import signup, myaccount
from userprofile.forms import LoginForm
from django.contrib.auth.views import LogoutView
from lead.views import add_lead, leads_list,leads_detail,leads_delete,leads_edit

urlpatterns = [
    path('about/',about,name='about'),
    path('myaccount/',myaccount,name='myaccount'),
    path('index/',index,name='index'),
    path('signup/',signup,name='signup'),
    path('log-in/', views.LoginView.as_view(template_name='userprofile/login.html', authentication_form=LoginForm), name='login'),
    path('logout/', UserLogoutView.as_view(http_method_names = ['get', 'post', 'options'] ), name='logout'),
    
    path('dashboard/',dashboard,name='dashboard'),
    path('add_lead/', add_lead, name='add_lead'),
    path('leads_list/',leads_list, name='leads_list' ),
    path('<int:pk>/', leads_detail, name='leads_detail'),
    path('delete/<int:pk>/', leads_delete, name='leads_delete'),
    path('edit/<int:pk>/', leads_edit, name='leads_edit'),
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)