#from urllib import request
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views import View
from .forms import AddLeadForm
from .models import Lead
from client.models import Client
from team.models import Plan, Team
from django.views.generic import ListView, DetailView, DeleteView, UpdateView, CreateView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin



""""  
class LeadListView(ListView):
    model = Lead

@method_decorator(login_required)
def dispatch(self, *args, **kwargs):
    return super().dispatch(*args, **kwargs)

def get_queryset(self):
     queryset = super(LeadListView, self).get_queryset()
     team = Team.objects.filter(created_by=self.request.user)[0]
     lead = Lead.objects.filter(created_by=self.request.user)
     return queryset.filter(lead=lead,team=team,created_by=self.request.user, converted_to_client=False)
""" 
    
    



@login_required
def leads_list(request):
    leads = Lead.objects.filter(created_by=request.user,converted_to_client=False)

    return render(request, 'lead/leads_list.html',{
       'leads': leads   
    })  



class LeadDetailView(LoginRequiredMixin, DetailView):
    model = Lead

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
     return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
       # context['form'] = AddCommentForm()
       # context['fileform'] = AddFileForm()

        return context

    def get_queryset(self):
        queryset = super(LeadDetailView, self).get_queryset()
        #team = self.request.user.userprofile.active_team

        return queryset.filter(created_by=self.request.user, pk=self.kwargs.get('pk'))
    

""""
@login_required
def leads_detail(request,pk):
    lead = get_object_or_404(Lead, created_by=request.user, pk=pk)
    

    return render(request, 'lead/leads_detail.html',{
       'lead': lead   
    })
"""
class LeadDeleteView(LoginRequiredMixin, DeleteView):
    model = Lead
    success_url = reverse_lazy('leads_list')

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
     return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super(LeadDeleteView, self).get_queryset()
        #team = self.request.user.userprofile.active_team

        return queryset.filter(created_by=self.request.user, pk=self.kwargs.get('pk'))
    
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

""""
@login_required
def leads_delete(request,pk):
    lead = get_object_or_404(Lead, created_by=request.user, pk=pk)
    lead.delete()
    messages.success(request, f"the lead was deleted!")
    return redirect('leads:list')
 """      

class LeadUpdateView(LoginRequiredMixin, UpdateView):
    model = Lead
    fields = ('name', 'email', 'description', 'priority', 'status',)
    success_url = reverse_lazy('leads_list')

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
     return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit lead'

        return context

    def get_queryset(self):
        queryset = super(LeadUpdateView, self).get_queryset()
        #team = self.request.user.userprofile.active_team

        return queryset.filter(created_by=self.request.user, pk=self.kwargs.get('pk'))





""""
@login_required
def leads_edit(request,pk):
   lead = get_object_or_404(Lead, created_by=request.user, pk=pk)
   if request.method =='POST':  
     form = AddLeadForm(request.POST, instance=lead)

     if form.is_valid():
            lead = form.save()
            
            
            
            lead.save()
            messages.success(request, f"the change was saved!")
            
     return redirect('/leads_list/')
   else:
     form = AddLeadForm(instance=lead) 
     
   return render(request, 'lead/leads_edit.html',{
    'form':form
 })
"""


class LeadCreateView(LoginRequiredMixin, CreateView):
    model = Lead
    fields = ('name', 'email', 'description', 'priority', 'status',)
    success_url = reverse_lazy('leads_list')

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
     return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #team = self.request.user.userprofile.get_active_team()
        team = Team.objects.filter(created_by=self.request.user)[0]
        context['team'] = team
        context['title'] = 'Add lead'

        return context

    def form_valid(self, form):
        team = Team.objects.filter(created_by=self.request.user)[0]
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user
       # self.object.team = self.request.user.userprofile.get_active_team()
        self.object.team = team
        self.object.save()
        
        return redirect(self.get_success_url())

""""
@login_required
def add_lead(request):
   team = Team.objects.filter(created_by=request.user)[0]
   
   if request.method =='POST':  
     form = AddLeadForm(request.POST)
     if form.is_valid():
            team = Team.objects.filter(created_by=request.user)[0]
            lead = form.save(commit=False)
            
            
            lead.created_by = request.user
            lead.team = team
            lead.save()
            messages.success(request, f"the lead was created!")
     return redirect('/leads:list/')
   else:
     form = AddLeadForm() 
     
   return render(request, 'lead/add_lead.html',{
    'form':form,
    'team':team
    
 })
"""

class ConvertToClientView( View):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')

        #team = self.request.user.userprofile.active_team
        team = Team.objects.filter(created_by=request.user)[0]
        lead = get_object_or_404(Lead, team=team, pk=pk)

        #team = self.request.user.userprofile.get_active_team()

        client = Client.objects.create(
            name=lead.name,
            email=lead.email,
            description=lead.description,
            created_by=request.user,
            team=team,
        )

        lead.converted_to_client = True
        lead.save()

        # Convert lead comments to client comments

        #comments = lead.comments.all()

       #for comment in comments:
            #ClientComment.objects.create(
               # client = client,
                #content = comment.content,
               #created_by = comment.created_by,
               # team = team
           # )
        
        # Show message and redirect

        messages.success(request, 'The lead was converted to a client.')

        return redirect('leads_list')


"""
@login_required
def convert_to_client(request,pk):
    lead = get_object_or_404(Lead, created_by=request.user, pk=pk)
    team = Team.objects.filter(created_by=request.user)[0]
    client = Client.objects.create(
            name=lead.name,
            email=lead.email,
            description=lead.description,
            created_by=request.user,
            team=team,

    )
    
          
    lead.converted_to_client = True
    lead.save()
    messages.success(request, f"the lead was converted to a client!")   
    return redirect('/leads:list/')
   """