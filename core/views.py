import datetime
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render,redirect
from django.contrib.auth.views import LogoutView
from django.contrib.auth import logout
from django.contrib.auth.views import LogoutView
import os
from client.models import Client
from team.models import Team
from django.db.models import Q
import glob
from pathlib import Path


class UserLogoutView(LogoutView):

    def get(self, request):
        logout(request)
        return redirect('login')
    
def index(request):
  #print(os.path.join(os.getcwd(), 'callerID2025-19.txt'))
  return render(request,'core/index.html')

def about(request):
 
  return render(request,'core/about.html')



def getfirstline(request):
    today = datetime.date.today()
    month = today.month
    year = today.year
    
    lenmonth = len(str(month))
    if lenmonth > 1:
     path = "C:\Mdr\CallerID"
    
     
     
     
    
    
    
     with open( path+str(year)+'-'+str(month)+'.txt','r') as f:
       try:  # catch OSError in case of a one line file 
         f.seek(-2, os.SEEK_END)
         while f.read(1) != b'\n':
            f.seek(-2, os.SEEK_CUR)
       except OSError:
        f.seek(0)
    
    

       last_line =  f.readlines()[-1]
     
      
       last_line = last_line[27:]
      
       request.session['idempresa'] =  last_line
       
      

       clients = Client.objects.all()
        
       
        
       return render(request, 'core/about.html', {
        'cliens': last_line,
        'years': year,
        'months': month,
        'numbers': clients,
        
        
        })
      
    
    else:
     today = datetime.date.today()
     month = today.month
     year = today.year
     lenmonth = len(str(month))
    
     path = "C:\Mdr\CallerID"
   

     
     
    try:
     with open( path+str(year)+'-'+'0'+str(month)+'.txt','r') as f:
      
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
       #response = HttpResponse("Cookie is set!")
       #response.set_cookie('my_cookie', last_line)
    
       clients = Client.objects.all()
       return render(request, 'core/about.html', {
        'cliens': last_line,
        'years': year,
        'months': month,
        'numbers': clients,
         
        })
    
    except FileNotFoundError:
     return render(request, 'core/about.html', {
        'messages':['No calls as of yet!'],
        
         
        })
    
    
      
  
    


  