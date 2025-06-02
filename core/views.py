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
import json
import hashlib
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import urllib3
import ssl
from django.utils import timezone

class UserLogoutView(LogoutView):

    def get(self, request):
        logout(request)
        return redirect('login')
    
def index(request):
  #print(os.path.join(os.getcwd(), 'callerID2025-19.txt'))
  return render(request,'core/index.html')

def about(request):
 
  return render(request,'core/about.html')







# Disable SSL warnings completely
urllib3.disable_warnings()
requests.packages.urllib3.disable_warnings()

@csrf_exempt
@require_http_methods(["GET", "POST"])
def getfirstline(request):
    """
    Django view to collect incoming caller ID from UCM6202 Grandstream API
    and save it to CSV file for POS system
    """
    try:
        # API configuration
        api_url = "http://192.168.20.216:8089/api"
        username = "cdrapi"
        password = "cdrapi123"
        
        headers = {
            "Connection": "close",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        
        # Create session with complete SSL bypass
        session = requests.Session()
        session.verify = False
        session.trust_env = False
        
        # Try to use TLS 1.0 which older devices often support
        try:
            import ssl
            session.mount('https://', requests.adapters.HTTPAdapter())
        except:
            pass
        
        # Step 1: Get challenge token
        challenge_payload = {
            "request": {
                "action": "challenge",
                "user": username
            }
        }
        
        print("Attempting challenge request...")  # Debug
        
        response = session.post(
            api_url,
            json=challenge_payload,
            headers=headers,
            verify=False,
            timeout=30
        )
        
        print(f"Challenge response status: {response.status_code}")  # Debug
        
        if response.status_code != 200:
            return JsonResponse({
                "error": f"Failed to get challenge token. Status: {response.status_code}",
                "response_text": response.text
            }, status=500)
        
        challenge_data = response.json()
        challenge = challenge_data['response']['challenge']
        
        # Step 2: Create MD5 token
        token = hashlib.md5((challenge + password).encode()).hexdigest()
        
        # Step 3: Login with token
        login_payload = {
            "request": {
                "action": "login",
                "token": token,
                "user": username
            }
        }
        
        print("Attempting login request...")  # Debug
        
        response = session.post(
            api_url,
            json=login_payload,
            headers=headers,
            verify=False,
            timeout=30
        )
        
        if response.status_code != 200:
            return JsonResponse({
                "error": f"Login failed. Status: {response.status_code}",
                "response_text": response.text
            }, status=500)
        
        login_data = response.json()
        cookie = login_data['response']['cookie']
        
        # Step 4: Get unbridged channels (caller ID)
        channels_payload = {
            "request": {
                "action": "listUnBridgedChannels",
                "cookie": cookie
            }
        }
        
        print("Attempting channels request...")  # Debug
        
        response = session.post(
            api_url,
            json=channels_payload,
            headers=headers,
            verify=False,
            timeout=30
        )
        
        if response.status_code != 200:
            return JsonResponse({
                "error": f"Failed to get channels. Status: {response.status_code}",
                "response_text": response.text
            }, status=500)
        
        channels_data = response.json()
        
        # Get current datetime
        current_datetime = datetime.datetime.now()
        formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
        
        # Define path for latest call file - adjust this path as needed for your POS system
        latest_call_file = os.path.join(os.getcwd(), 'latest_call.txt')
        # Alternative paths you might want to use:
        # latest_call_file = 'C:/POS_Data/latest_call.txt'
        # latest_call_file = '/var/www/shared/latest_call.txt'
        
        # Extract caller ID and save to file
        if ('response' in channels_data and 
            'channel' in channels_data['response'] and 
            len(channels_data['response']['channel']) > 0):
            
            caller_id = channels_data['response']['channel'][0]['callernum']
            
            # Save latest call to single-line file for immediate POS access
            try:
                with open(latest_call_file, 'w') as f:
                    f.write(f"{caller_id},{formatted_datetime}")
                
                print(f"Saved latest call: Caller: {caller_id}, Time: {formatted_datetime}")
                
            except Exception as file_error:
                print(f"File save error: {str(file_error)}")
            
            # Store in session (equivalent to $_SESSION['userinc'])
            request.session['userinc'] = caller_id
            
            today = datetime.date.today()
            month = today.month           
            year = today.year
            clients = Client.objects.all()
            
            return render(request, 'core/about.html', {
                'cliens': caller_id,
                'years': year,
                'months': month,
                'numbers': clients,
            })
        else:
            caller_id = "No active channels found"
            
            # Optionally save "no channels" status (you can remove this if not needed)
            try:
                with open(latest_call_file, 'w') as f:
                    f.write(f"NO_CHANNELS,{formatted_datetime}")
                
                print(f"No channels found at: {formatted_datetime}")
                
            except Exception as file_error:
                print(f"File save error: {str(file_error)}")
            
            today = datetime.date.today()
            month = today.month           
            year = today.year
            clients = Client.objects.all()
            
            return render(request, 'core/about.html', {
                'cliens': caller_id,
                'years': year,
                'months': month,
                'numbers': clients,
            })
            
    except requests.exceptions.SSLError as e:
        # If SSL still fails, suggest using HTTP instead
        return JsonResponse({
            "error": f"SSL Error: {str(e)}", 
            "suggestion": "Try changing the URL to HTTP (http://192.168.20.216:8089/api) if the device supports it"
        }, status=500)
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": f"Network error: {str(e)}"}, status=500)
    except KeyError as e:
        return JsonResponse({"error": f"Invalid API response format: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)


# Optional: Helper function to read latest call for POS system
def get_latest_call_for_pos(request):
    """
    Simple endpoint that returns the latest call data in JSON format
    for your POS system to consume
    """
    try:
        latest_call_file = os.path.join(os.getcwd(), 'latest_call.txt')
        
        if os.path.exists(latest_call_file):
            with open(latest_call_file, 'r') as f:
                data = f.read().strip().split(',')
                if len(data) >= 2:
                    return JsonResponse({
                        'caller_id': data[0],
                        'datetime': data[1],
                        'status': 'success'
                    })
        
        return JsonResponse({
            'caller_id': '',
            'datetime': '',
            'status': 'no_data'
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)