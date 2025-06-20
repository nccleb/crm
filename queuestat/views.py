from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse  # Added HttpResponse here
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View
import urllib3
import json
import hashlib
import requests

from django.http import HttpResponse
import requests
import hashlib
import json
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

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

def test_api(request):
    """Django view to test API connectivity"""
    api_url = 'https://192.168.20.216:8089/api'
    output = []
    
    output.append("=== API Authentication Test ===\n")
    
    # Create session with legacy SSL support
    session = requests.Session()
    session.mount('https://', LegacyHTTPSAdapter())
    
    # Test basic connectivity
    output.append("Step 1: Testing basic connectivity...")
    try:
        response = session.get(api_url, verify=False, timeout=10)
        output.append(f"✓ Basic connectivity test: Status {response.status_code}")
    except Exception as e:
        output.append(f"✗ Cannot reach API: {e}")
        return HttpResponse("<pre>" + "\n".join(output) + "</pre>")
    
    # Test authentication flow
    output.append("\nStep 2: Testing challenge request...")
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
            "Content-Type": "application/json"
        }
        
        response = session.post(
            api_url,
            json=challenge_data,
            headers=headers,
            verify=False,
            timeout=30
        )
        
        output.append(f"Challenge response status: {response.status_code}")
        
        if response.status_code != 200:
            output.append(f"✗ Challenge failed with status {response.status_code}")
            output.append(f"Response body: {response.text}")
            return HttpResponse("<pre>" + "\n".join(output) + "</pre>")
            
        try:
            challenge_response = response.json()
            output.append(f"✓ Challenge response JSON parsed successfully")
        except json.JSONDecodeError:
            output.append(f"✗ Invalid JSON in challenge response: {response.text}")
            return HttpResponse("<pre>" + "\n".join(output) + "</pre>")
            
        challenge = challenge_response.get('response', {}).get('challenge')
        
        if not challenge:
            output.append(f"✗ No challenge found in response")
            output.append(f"Full response: {challenge_response}")
            return HttpResponse("<pre>" + "\n".join(output) + "</pre>")
        
        output.append(f"✓ Challenge received: {challenge}")
        
        # Step 2: Generate token and login
        output.append("\nStep 3: Testing login with token...")
        password = "cdrapi123"
        token = hashlib.md5((challenge + password).encode()).hexdigest()
        output.append(f"Generated token: {token}")
        
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
        
        output.append(f"Login response status: {response.status_code}")
        
        if response.status_code != 200:
            output.append(f"✗ Login failed with status {response.status_code}")
            output.append(f"Response body: {response.text}")
            return HttpResponse("<pre>" + "\n".join(output) + "</pre>")
            
        try:
            login_response = response.json()
            output.append(f"✓ Login response JSON parsed successfully")
        except json.JSONDecodeError:
            output.append(f"✗ Invalid JSON in login response: {response.text}")
            return HttpResponse("<pre>" + "\n".join(output) + "</pre>")
            
        cookie = login_response.get('response', {}).get('cookie')
        
        if cookie:
            output.append(f"✅ SUCCESS! Cookie received: {cookie}")
            output.append(f"\nFull login response: {login_response}")
        else:
            output.append(f"✗ No cookie in login response")
            output.append(f"Full response: {login_response}")
            
    except requests.exceptions.RequestException as e:
        output.append(f"✗ Request error during authentication: {e}")
    except Exception as e:
        output.append(f"✗ Unexpected error during authentication: {e}")
    
    output.append("\n=== Test Complete ===")
    return HttpResponse("<pre>" + "\n".join(output) + "</pre>")


class AgentSearchView(View):
    """View for the search form (equivalent to test476.php)"""
    
    def get(self, request):
        # Handle URL parameters like the original PHP
        page = request.GET.get('page', '')
        page1 = request.GET.get('page1', '')
        
        # Store in session like the original
        request.session['page'] = page
        request.session['page1'] = page1
        
        context = {
            'page': page,
            'page1': page1,
        }
        return render(request, 'queuestat/agent_search.html', context)

class AgentDetailsView(View):
    """View for processing search and displaying results (equivalent to test475.php)"""
    
    def post(self, request):
        # Validate form data
        sta = request.POST.get('sta')
        end = request.POST.get('end')
        que = request.POST.get('que')
        age = request.POST.get('age')
        con = request.POST.get('con')
        
        # Check if required fields are present
        if not all([sta, end]) or que is None or age is None or con is None:
            messages.error(request, 'Missing Entry!')
            return redirect('agent_search')
        
        # Clean input data (equivalent to test_input function)
        sta = self.clean_input(sta)
        end = self.clean_input(end)
        que = self.clean_input(que) 
        age = self.clean_input(age)
        con = self.clean_input(con)
        
        try:
            # Get API data
            cookie = self.get_api_cookie()
            if not cookie:
                messages.error(request, 'Failed to authenticate with API')
                return redirect('queueatats:agent_search')
                
            # Get queue statistics
            queue_data = self.get_queue_data(cookie, sta, end, que, age)
            
            if not queue_data:
                context = {
                    'reload_needed': True,
                    'search_params': {
                        'sta': sta, 'end': end, 'que': que, 'age': age, 'con': con
                    }
                }
                return render(request, 'queuestat/agent_details.html', context)
            
            # Filter data based on connection status
            filtered_data = self.filter_data(queue_data, con)
            
            context = {
                'agent_data': filtered_data,
                'search_params': {
                    'sta': sta, 'end': end, 'que': que, 'age': age, 'con': con
                },
                'reload_needed': False
            }
            
            return render(request, 'queuestat/agent_details.html', context)
            
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('agent_search')
    
    def clean_input(self, data):
        """Equivalent to PHP test_input function"""
        if data is None:
            return ''
        data = str(data).strip().strip('/')
        # Django automatically handles HTML escaping in templates
        return data
    


    
    def get_api_cookie(self):
        api_url = 'https://192.168.20.216:8089/api'
        
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
                "Content-Type": "application/json"
            }
            
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
            challenge = challenge_response.get('response', {}).get('challenge')
            
            if not challenge:
                return None
            
            # Step 2: Generate token
            password = "cdrapi123"
            token = hashlib.md5((challenge + password).encode()).hexdigest()
            
            # Step 3: Login with token
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
            cookie = login_response.get('response', {}).get('cookie')
            
            return cookie
            
        except Exception as e:
            print(f"API authentication error: {e}")
            return None





    def get_queue_data(self, cookie, start_time, end_time, queue, agent):
        api_url = 'https://192.168.20.216:8089/api'
        
        # Create session with legacy SSL support
        session = requests.Session()
        session.mount('https://', LegacyHTTPSAdapter())
        
        try:
            queue_request = {
                "request": {
                    "action": "queueapi",
                    "endTime": end_time,
                    "startTime": start_time,
                    "queue": queue,
                    "agent": agent,
                    "format": "json",
                    "statisticsType": "calldetail",
                    "cookie": cookie
                }
            }
            
            headers = {
                "Connection": "close",
                "Content-Type": "application/json"
            }
            
            response = session.post(  # Changed from requests.post to session.post
                api_url,
                json=queue_request,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            
            # Check if reload is needed (equivalent to PHP is_int check)
            if isinstance(data.get('status'), int):
                return None
                
            return data.get('queue_statistics', [])
            
        except Exception as e:
            print(f"Queue data error: {e}")
            return None

        
    
    def filter_data(self, queue_data, connection_filter):
        """Filter data based on connection status"""
        filtered_results = []
        
        for item in queue_data:
            agent_data = item.get('agent', {})
            
            # Skip entries where agent is "NONE"
            if agent_data.get('agent') == 'NONE':
                continue
                
            # Apply connection filter
            if connection_filter == 'yes':
                if agent_data.get('connect') != 'yes':
                    continue
            elif connection_filter == 'no':
                if agent_data.get('connect') != 'no':
                    continue
            # If connection_filter is neither 'yes' nor 'no', include all
            
            filtered_results.append(agent_data)
        
        return filtered_results
# Create your views here.
