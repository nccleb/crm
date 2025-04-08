from pyexpat.errors import messages
from django.shortcuts import get_object_or_404, render,redirect
from django.contrib.auth.views import LogoutView
from django.contrib.auth import logout
from django.contrib.auth.views import LogoutView
import os
from client.models import Client
from team.models import Team
from django.db.models import Q

class UserLogoutView(LogoutView):

    def get(self, request):
        logout(request)
        return redirect('login')
    
def index(request):
 
  return render(request,'core/index.html')

def about(request):
 
  return render(request,'core/about.html')



def getfirstline(request):
    team = request.user.userprofile.active_team
    #client = get_object_or_404(Client, pk=pk)
    #clients = team.clients.all()
    with open('C:\Mdr\CallerID2025-04.txt', 'r') as f:
        
     try:  # catch OSError in case of a one line file 
        f.seek(-2, os.SEEK_END)
        while f.read(1) != b'\n':
            f.seek(-2, os.SEEK_CUR)
     except OSError:
        f.seek(0)
    

     last_line =  f.readlines()[-1]
     
      
     last_line = last_line[27:]
     #parm_dict = {'phone_number': last_line}
     request.session['idempresa'] =  last_line
      
    
     clients = Client.objects.all()
     return render(request, 'core/about.html', {
        'cliens': last_line,
        'numbers': clients,
        
    })
      
    
   