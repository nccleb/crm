from django.shortcuts import render

# Create your views here.
import json
import hashlib
import requests
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .forms import StatisticsForm

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LegacyHTTPSAdapter(HTTPAdapter):
    """HTTPS Adapter that works with legacy SSL servers"""
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers('DEFAULT@SECLEVEL=1')
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)


def StatisticsQueueFormView(request):
    """Function-based view for queue statistics form"""
    if request.method == 'POST':
        form = StatisticsForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            queue_number = form.cleaned_data['queue_number']
            
            # Redirect to results view
            return redirect('stotisticss:statistics_queue_results')
    else:
        form = StatisticsForm()
    
    return render(request, 'stotistics/statistics_queue_form.html', {'form': form})


def StatisticsAgentFormView(request):
    """Function-based view for agent statistics form"""
    if request.method == 'POST':
        form = StatisticsForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            agent_number = form.cleaned_data['agent_number']
            
            # Redirect to results view
            return redirect('stotisticss:statistics_agent_results')
    else:
        form = StatisticsForm()
    
    return render(request, 'stotistics/statistics_agent_form.html', {'form': form})    


class StatisticsQueueResultView(View):
    """View for processing queue form and showing results"""
    
    def post(self, request):
        form = StatisticsForm(request.POST)
        
        if not form.is_valid():
            messages.error(request, 'Missing Entry!')
            return redirect('stotisticss:statistics_Queue_form')
        
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        queue_number = form.cleaned_data['queue_number']
        
        try:
            # API authentication and data retrieval
            api_data = self.get_api_data(start_date, end_date, queue_number)
            
            if api_data is None:
                messages.error(request, 'Failed to retrieve data from API')
                return redirect('stotisticss:statistics_Queue_form')
            
            # Get URL parameters from session
            page = request.session.get('os', request.GET.get('page', ''))
            page1 = request.session.get('p', '')
            request.session['os'] = page
            
            context = {
                'api_data': api_data,
                'start_date': start_date,
                'end_date': end_date,
                'queue': queue_number,
                'page': page,
                'page1': page1,
            }
            
            return render(request, 'stotistics/queue_statistics_results.html', context)
            
        except Exception as e:
            messages.error(request, f'Error processing request: {str(e)}')
            return redirect('stotisticss:statistics_Queue_form')
    
    def get_api_data(self, start_date, end_date, queue_number):
        """Handle API authentication and data retrieval"""
        # Create session with legacy SSL support
        session = requests.Session()
        session.mount('https://', LegacyHTTPSAdapter())

        try:
            # Step 1: Get challenge
            challenge_data = {
                "request": {
                    "action": "challenge",
                    "user": "cdrapi"
                }
            }
            
            headers = {
                "Connection": "close",
                "Content-Type": "application/json",
            }
            
            # Define the API URL
            api_url = 'https://192.168.20.216:8089/api'
            
            # Make challenge request
            response = session.post(
                api_url,
                json=challenge_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
            
            challenge_response = response.json()
            challenge = challenge_response['response']['challenge']
            
            # Step 2: Generate token
            password = "cdrapi123"
            token = hashlib.md5((challenge + password).encode()).hexdigest()
            
            # Step 3: Login
            login_data = {
                "request": {
                    "action": "login",
                    "token": token,
                    "user": "cdrapi"
                }
            }
            
            response = session.post(
                api_url,
                json=login_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
            
            login_response = response.json()
            cookie = login_response['response']['cookie']
            
            # Step 4: Get unbridged channels
            channels_data = {
                "request": {
                    "action": "listUnBridgedChannels",
                    "cookie": cookie
                }
            }
            
            response = session.post(
                api_url,
                json=channels_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                channels_response = response.json()
                # Get first channel if available
                if 'response' in channels_response and 'channel' in channels_response['response']:
                    if channels_response['response']['channel']:
                        channel = channels_response['response']['channel'][0]['channel']
            
            # Step 5: Get queue statistics
            queue_data = {
                "request": {
                    "action": "queueapi",
                    "endTime": end_date.strftime('%Y-%m-%d'),
                    "startTime": start_date.strftime('%Y-%m-%d'),
                    "queue": queue_number if queue_number else "",
                    "format": "json",
                    "cookie": cookie
                }
            }
            
            response = session.post(
                api_url,
                json=queue_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
            
            queue_response = response.json()
            
            # Check if status is integer (error condition)
            if isinstance(queue_response.get('status'), int):
                return {'reload_required': True}
            
            # Extract statistics
            if 'queue_statistics' in queue_response and queue_response['queue_statistics']:
                queue_info = queue_response['queue_statistics'][0]['queue']
                
                return {
                    'queuechairman': queue_info.get('queuechairman', ''),
                    'queue': queue_info.get('queue', ''),
                    'total_calls': queue_info.get('total_calls', ''),
                    'answered_calls': queue_info.get('answered_calls', ''),
                    'answered_rate': queue_info.get('answered_rate', ''),
                    'avg_wait': queue_info.get('avg_wait', ''),
                    'avg_talk': queue_info.get('avg_talk', ''),
                    'vq_total_calls': queue_info.get('vq_total_calls', ''),
                }
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            print(f"Data Processing Error: {e}")
            return None


class StatisticsAgentResultView(View):
    """View for processing queue form and showing results"""
    
    def post(self, request):
        form = StatisticsForm(request.POST)
        
        if not form.is_valid():
            messages.error(request, 'Missing Entry!')
            return redirect('stotisticss:statistics_Agent_form')
        
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        agent_number = form.cleaned_data['agent_number']
        
        try:
            # API authentication and data retrieval
            api_data = self.get_api_data(start_date, end_date, agent_number)
            
            if api_data is None:
                messages.error(request, 'Failed to retrieve data from API')
                return redirect('stotisticss:statistics_Agent_form')
            
            # Get URL parameters from session
            page = request.session.get('os', request.GET.get('page', ''))
            page1 = request.session.get('p', '')
            request.session['os'] = page
            
            context = {
                'api_data': api_data,
                'start_date': start_date,
                'end_date': end_date,
                'agent': agent_number,
                'page': page,
                'page1': page1,
            }
            
            return render(request, 'stotistics/agent_statistics_results.html', context)
            
        except Exception as e:
            messages.error(request, f'Error processing request: {str(e)}')
            return redirect('stotisticss:statistics_Agent_form')
    
    def get_api_data(self, start_date, end_date, agent_number):
        """Handle API authentication and data retrieval"""
        # Create session with legacy SSL support
        session = requests.Session()
        session.mount('https://', LegacyHTTPSAdapter())

        try:
            # Step 1: Get challenge
            challenge_data = {
                "request": {
                    "action": "challenge",
                    "user": "cdrapi"
                }
            }
            
            headers = {
                "Connection": "close",
                "Content-Type": "application/json",
            }
            
            # Define the API URL
            api_url = 'https://192.168.20.216:8089/api'
            
            # Make challenge request
            response = session.post(
                api_url,
                json=challenge_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
            
            challenge_response = response.json()
            challenge = challenge_response['response']['challenge']
            
            # Step 2: Generate token
            password = "cdrapi123"
            token = hashlib.md5((challenge + password).encode()).hexdigest()
            
            # Step 3: Login
            login_data = {
                "request": {
                    "action": "login",
                    "token": token,
                    "user": "cdrapi"
                }
            }
            
            response = session.post(
                api_url,
                json=login_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
            
            login_response = response.json()
            cookie = login_response['response']['cookie']
            
            # Step 4: Get unbridged channels
            channels_data = {
                "request": {
                    "action": "listUnBridgedChannels",
                    "cookie": cookie
                }
            }
            
            response = session.post(
                api_url,
                json=channels_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                channels_response = response.json()
                # Get first channel if available
                if 'response' in channels_response and 'channel' in channels_response['response']:
                    if channels_response['response']['channel']:
                        channel = channels_response['response']['channel'][0]['channel']
            
            # Step 5: Get agent statistics
            agent_data = {
                "request": {
                    "action": "queueapi",
                    "endTime": end_date.strftime('%Y-%m-%d'),
                    "startTime": start_date.strftime('%Y-%m-%d'),
                    "agent": agent_number if agent_number else "",
                    "format": "json",
                    "cookie": cookie
                }
            }
            
            response = session.post(
                api_url,
                json=agent_data ,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
            
            agent_response = response.json()
            
            # Check if status is integer (error condition)
            if isinstance(agent_response.get('status'), int):
                return {'reload_required': True}
            
            # Extract statistics
            if 'queue_statistics' in agent_response and agent_response['queue_statistics']:
                agent_info = agent_response['queue_statistics'][0]['agent']
                
                return {
                    'queuechairman': agent_info.get('queuechairman', ''),
                    'agent': agent_info.get('agent', ''),
                    'total_calls': agent_info.get('total_calls', ''),
                    'answered_calls': agent_info.get('answered_calls', ''),
                    'answered_rate': agent_info.get('answered_rate', ''),
                    
                    'avg_talk': agent_info.get('avg_talk', ''),
                    'vq_total_calls': agent_info.get('vq_total_calls', ''),
                }
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            print(f"Data Processing Error: {e}")
            return None



class StatisticsFormView(View):
    """View for displaying the statistics form (equivalent to test462.php)"""
    
    def get(self, request):
        form = StatisticsForm()
        
        # Get session data similar to PHP
        session_data = request.session.get('ses', None)
        cookie_data = request.COOKIES.get('user', None)
        
        # Get URL parameters
        page = request.GET.get('page', '')
        page1 = request.GET.get('page1', '')
        
        # Store in session
        request.session['o'] = page
        request.session['p'] = page1
        
        context = {
            'form': form,
            'session_data': session_data,
            'cookie_data': cookie_data,
            'page': page,
            'page1': page1,
        }
        
        return render(request, 'stotistics/statistics_form.html', context)

class StatisticsResultView(View):
    """View for processing form and showing results (equivalent to test461.php)"""
    
    def post(self, request):
        form = StatisticsForm(request.POST)
        
        if not form.is_valid():
            messages.error(request, 'Missing Entry!')
            return redirect('stotisticss:statistics_form')
        
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        
        try:
            # API authentication and data retrieval
            api_data = self.get_api_data(start_date, end_date)
            
            if api_data is None:
                messages.error(request, 'Failed to retrieve data from API')
                return redirect('stotisticss:statistics_form')
            
            # Get URL parameters from session
            page = request.session.get('os', request.GET.get('page', ''))
            page1 = request.session.get('p', '')
            request.session['os'] = page
            
            context = {
                'api_data': api_data,
                'start_date': start_date,
                'end_date': end_date,
                'page': page,
                'page1': page1,
            }
            
            return render(request, 'stotistics/statistics_results.html', context)
            
        except Exception as e:
            messages.error(request, f'Error processing request: {str(e)}')
            return redirect('stotisticss:statistics_form')
    
    def get_api_data(self, start_date, end_date):
        """Handle API authentication and data retrieval"""

         # Create session with legacy SSL support
        session = requests.Session()
        session.mount('https://', LegacyHTTPSAdapter())




        try:
            # Step 1: Get challenge
            challenge_data = {
                "request": {
                    "action": "challenge",
                    "user": "cdrapi"
                }
            }
            
            headers = {
                "Connection": "close",
                "Content-Type": "application/json",
            }
            
            # Define the API URL
            api_url = 'https://192.168.20.216:8089/api'
            # Make challenge request
            response = session.post(  # Changed from requests.post to session.post
                api_url,
                json=challenge_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
            
            challenge_response = response.json()
            challenge = challenge_response['response']['challenge']
            
            # Step 2: Generate token
            password = "cdrapi123"
            token = hashlib.md5((challenge + password).encode()).hexdigest()
            
            # Step 3: Login
            login_data = {
                "request": {
                    "action": "login",
                    "token": token,
                    "user": "cdrapi"
                }
            }
            
            response = session.post(  # Changed from requests.post to session.post
                api_url,
                json=login_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            
            if response.status_code != 200:
                return None
            
            login_response = response.json()
            cookie = login_response['response']['cookie']
            
            # Step 4: Get unbridged channels
            channels_data = {
                "request": {
                    "action": "listUnBridgedChannels",
                    "cookie": cookie
                }
            }
            
            response = session.post(  # Changed from requests.post to session.post
                api_url,
                json=channels_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            
            if response.status_code == 200:
                channels_response = response.json()
                # Get first channel if available
                if 'response' in channels_response and 'channel' in channels_response['response']:
                    if channels_response['response']['channel']:
                        channel = channels_response['response']['channel'][0]['channel']
            
            # Step 5: Get queue statistics
            queue_data = {
                "request": {
                    "action": "queueapi",
                    "endTime": end_date.strftime('%Y-%m-%d'),
                    "startTime": start_date.strftime('%Y-%m-%d'),
                    "format": "json",
                    "cookie": cookie
                }
            }
            
            response = session.post(  # Changed from requests.post to session.post
                api_url,
                json=queue_data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            
            if response.status_code != 200:
                return None
            
            queue_response = response.json()
            
            # Check if status is integer (error condition)
            if isinstance(queue_response.get('status'), int):
                return {'reload_required': True}
            
            # Extract statistics
            if 'queue_statistics' in queue_response and queue_response['queue_statistics']:
                total_stats = queue_response['queue_statistics'][0]['total']
                
                return {
                    'queuechairman': total_stats.get('queuechairman', ''),
                    'total_calls': total_stats.get('total_calls', ''),
                    'abandoned_rate': total_stats.get('abandoned_rate', ''),
                    'avg_wait': total_stats.get('avg_wait', ''),
                    'avg_talk': total_stats.get('avg_talk', ''),
                    'vq_total_calls': total_stats.get('vq_total_calls', ''),
                    'reload_required': False
                }
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"API Request Error: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            print(f"Data Processing Error: {e}")
            return None