from pyexpat.errors import messages
from django.shortcuts import render,redirect
from django.contrib.auth.views import LogoutView
from django.contrib.auth import logout
from django.contrib.auth.views import LogoutView

class UserLogoutView(LogoutView):

    def get(self, request):
        logout(request)
        return redirect('login')
    
def index(request):
 
  return render(request,'core/index.html')

def about(request):
 
  return render(request,'core/about.html')


   