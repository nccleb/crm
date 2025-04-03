from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from lead.models import Lead
from client.models import Client
from team.models import Team

@login_required
def dashboard(request):
    team = request.user.userprofile.active_team

    leads = Lead.objects.filter( converted_to_client=False).order_by('-created_at')[0:5]
    clients = Client.objects.filter().order_by('-created_at')[0:5]

    return render(request, 'dashboard/dashboard.html', {
        'leads': leads,
        'clients': clients,
    })