import csv

import psycopg2
from django.db.models import Q
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Client
from .forms import AddClientForm, AddCommentForm, AddFileForm, AdddClientForm
from team.models import Team


@login_required
def clients_export(request):
    team = request.user.userprofile.active_team
    
    clients = team.clients.all()

    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="clients.csv"'},
    )

    writer = csv.writer(response)
    writer.writerow(['Name','Email','Description', 'Created at', 'Modified at','Created by','team','phone_number','address'  ])

    for client in clients:
        writer.writerow([client.name,client.email,client.description,client.created_at, client.modified_at, client.created_by,client.team, client.phone_number,client.address])
    
    return response




@login_required
def ingest_data(request):
   
    conn = psycopg2.connect("host = 127.0.0.1 dbname = mydatabase user = postgres password = A1A1a1a1 ")
   
    #connect to POSTGRESQL
    #conn = connect_to_db()
    cur = conn.cursor()
    #open the csv file
    with open('C:\data.csv','r') as file:
        data_reader = csv.reader(file)
        next(data_reader) #skip the header row
        #insert each header row into the table 
        for row in data_reader:
           cur.execute("INSERT INTO client_client (name,email,description,phone_number,address) values (%s,%s,%s,%s,%s)", row)
    #commit and close the connection
    conn.commit() 
    cur.close
    conn.close
    messages.success(request, f"Data ingested successfully")      
    return redirect('clients:list')
    #return HttpResponse("Data ingested successfully")
    #print("Data ingested successfully")    
    if __name__=="__main__":
        ingest_data() 




@login_required
def clients_search(request):
   
    name = request.GET.get('search', False)
    clients =  Client.objects.filter(Q(name__icontains=name))

    return render(request, 'client/clients_search.html', {
        'clients': clients
    })


@login_required
def clients_search_n(request):
   
    phone_number = request.GET.get('search_n', False)
    clients =  Client.objects.filter(Q(phone_number__icontains = phone_number))

    return render(request, 'client/clients_search.html', {
        'clients': clients
    })


@login_required
def clients_list(request):
    #team = request.user.userprofile.active_team
    clients =  Client.objects.filter()

    return render(request, 'client/clients_list.html', {
        'clients': clients
    })



@login_required
def clients_add_file(request, pk):
    if request.method == 'POST':
        form = AddFileForm(request.POST, request.FILES)
        
        if form.is_valid():
            file = form.save(commit=False)
            file.team = request.user.userprofile.active_team
            file.client_id = pk
            file.created_by = request.user
            file.save()

           
    return redirect('clients:detail', pk=pk)



@login_required
def clients_detail(request,pk):
    
    client = get_object_or_404(Client, pk=pk)
   
    if request.method == 'POST':
        form = AddCommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.team = request.user.userprofile.active_team
            comment.created_by = request.user
            comment.client = client
            comment.save()

            return redirect('clients:detail', pk=pk)
    else:
        form = AddCommentForm()

    return render(request, 'client/clients_detail.html', {
        'client': client,
        'form': form,
        'fileform': AddFileForm(),
    })

@login_required
def clients_add(request):
   if request.method =='POST':  
     form = AddClientForm(request.POST)
     if form.is_valid():
            
            client = form.save(commit=False)
            
            
            client.created_by = request.user
            client.team = request.user.userprofile.active_team
            client.save()
            messages.success(request, f"the client was created!")

     else:
          messages.success(request, f"the client was not  created!")      
     return redirect('clients:list')
     
            
            
           
        
     
   else:
     form = AddClientForm() 
     
   return render(request, 'client/clients_add.html',{
    'form':form
 })


@login_required
def clients_addd(request):
   if request.method =='POST':  
     form = AddClientForm(request.POST)
     if form.is_valid():
            
            client = form.save(commit=False)
            
            client.phone_number = "05600015"
            client.created_by = request.user
            client.team = request.user.userprofile.active_team
            client.save()
            messages.success(request, f"the client was created!")

     else:
          messages.success(request, f"the client was not  created!")      
     return redirect('clients:list')
     
            
            
           
        
     
   else:
     form = AdddClientForm() 
     
   return render(request, 'client/clients_addd.html',{
    'form':form
 })
     
  







@login_required
def clients_edit(request, pk):
    
    client = get_object_or_404(Client,  pk=pk)

    if request.method == 'POST':
        form = AddClientForm(request.POST, instance=client)

        if form.is_valid():
            form.save()

            messages.success(request, 'The changes was saved.')

            return redirect('clients:list')
    else:
        form = AddClientForm(instance=client)
    
    return render(request, 'client/clients_edit.html', {
        'form': form
    })




@login_required
def clients_delete(request,pk):
    client = get_object_or_404(Client,  pk=pk)
    client.delete()
    messages.success(request, f"the client was deleted!")
    return redirect('clients:list')


