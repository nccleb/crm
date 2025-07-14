# Enhanced views.py with integrated alert system
import traceback
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import urllib3
import json
import hashlib
import requests
import ssl
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time

from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

import asyncio
from django.http import HttpResponse
from asgiref.sync import sync_to_async


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class CallAlertManager:
    """Manages call queue alerts for UCM6202"""
    
    def __init__(self):
        self.alert_thresholds = {
            'wait_time_warning': getattr(settings, 'CALL_WAIT_WARNING_SECONDS', 30),
            'wait_time_critical': getattr(settings, 'CALL_WAIT_CRITICAL_SECONDS', 60),
            'unanswered_threshold': getattr(settings, 'CALL_UNANSWERED_SECONDS', 90),
        }
        
        # Track sent alerts to avoid spam
        self.sent_alerts = {}
        
        # Email settings
        self.alert_recipients = getattr(settings, 'CALL_ALERT_RECIPIENTS', [])
    
    
    def check_queue_for_alerts(self, queue_data, queue_name="Unknown"):
        """Check queue data for calls requiring alerts - focus on most recent calls"""
        alerts_needed = []
        current_time = datetime.now()
        
        # Group calls by caller number to track progression
        caller_calls = {}
        
        # First pass: organize calls by caller number
        for item in queue_data:
            agent_data = item.get('agent', {})
            
            # Skip if agent is "NONE" 
            if agent_data.get('agent') == 'NONE':
                continue
            
            caller_num = agent_data.get('callernum', 'Unknown')
            start_time_str = agent_data.get('start_time', '')
            
            # Use caller number as key, store the call data
            if caller_num not in caller_calls:
                caller_calls[caller_num] = []
            
            caller_calls[caller_num].append({
                'agent_data': agent_data,
                'start_time_str': start_time_str,
                'caller_num': caller_num
            })
        
        # Second pass: process only the most recent call per caller
        for caller_num, calls in caller_calls.items():
            # Sort by start time to get the most recent call
            calls.sort(key=lambda x: x['start_time_str'], reverse=True)
            most_recent_call = calls[0]  # Get the latest call
            
            agent_data = most_recent_call['agent_data']
            start_time_str = most_recent_call['start_time_str']
            
            # Extract call information from the most recent call
            connect_status = agent_data.get('connect', 'unknown')
            wait_time_str = agent_data.get('wait_time', '0')
            
            # Calculate wait time in seconds
            wait_seconds = self.parse_wait_time(wait_time_str)
            
            # Check for unanswered calls (connect = 'no' and wait time exceeded)
            if connect_status == 'no' and wait_seconds >= self.alert_thresholds['unanswered_threshold']:
                alert_key = f"{caller_num}_{start_time_str}_unanswered"
                
                # Avoid duplicate alerts within the time window
                if self.should_send_alert(alert_key):
                    alert_data = {
                        'type': 'UNANSWERED_CALL',
                        'severity': 'CRITICAL',
                        'queue_name': queue_name,
                        'caller_number': caller_num,
                        'wait_time_seconds': wait_seconds,
                        'wait_time_display': wait_time_str,
                        'start_time': start_time_str,
                        'agent': agent_data.get('agent', 'None'),
                        'extension': agent_data.get('extension', 'None'),
                        'queuechairman': agent_data.get('queuechairman', 'Unknown'),
                        'call_count': len(calls),  # How many calls from this number
                        'is_most_recent': True
                    }
                    alerts_needed.append(alert_data)
                    self.mark_alert_sent(alert_key)
                    
                    # Log for debugging
                    logger.info(f"UNANSWERED CALL ALERT: {caller_num} waiting {wait_seconds}s (most recent of {len(calls)} calls)")
            
            # Check for long wait times (still waiting) - only for the most recent call
            # elif connect_status == 'no' and wait_seconds >= self.alert_thresholds['wait_time_critical']:
            #     alert_key = f"{caller_num}_{start_time_str}_longwait"
                
            #     if self.should_send_alert(alert_key):
            #         alert_data = {
            #             'type': 'LONG_WAIT_TIME',
            #             'severity': 'HIGH',
            #             'queue_name': queue_name,
            #             'caller_number': caller_num,
            #             'wait_time_seconds': wait_seconds,
            #             'wait_time_display': wait_time_str,
            #             'start_time': start_time_str,
            #             'agent': agent_data.get('agent', 'None'),
            #             'queuechairman': agent_data.get('queuechairman', 'Unknown'),
            #             'call_count': len(calls),
            #             'is_most_recent': True
            #         }
            #         alerts_needed.append(alert_data)
            #         self.mark_alert_sent(alert_key)
                    
            #         # Log for debugging
            #         logger.info(f"LONG WAIT ALERT: {caller_num} waiting {wait_seconds}s (most recent of {len(calls)} calls)")
        
        return alerts_needed




    
    def parse_wait_time(self, wait_time_str):
        """Parse wait time string to seconds (e.g., '00:01:30' to 90)"""
        try:
            if ':' in wait_time_str:
                parts = wait_time_str.split(':')
                if len(parts) == 3:  # HH:MM:SS
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = int(parts[2])
                    return hours * 3600 + minutes * 60 + seconds
                elif len(parts) == 2:  # MM:SS
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    return minutes * 60 + seconds
            else:
                return int(wait_time_str)
        except (ValueError, IndexError):
            return 0
    
    def should_send_alert(self, alert_key):
        """Check if we should send alert (avoid spam)"""
        current_time = datetime.now()
        last_sent = self.sent_alerts.get(alert_key)
        
        if not last_sent:
            return True
        
        # Don't send same alert within 24 hours
        if (current_time - last_sent).total_seconds() < 86000:
            return False
        
        return True
    
    def mark_alert_sent(self, alert_key):
        """Mark alert as sent"""
        self.sent_alerts[alert_key] = datetime.now()
        
        # Clean old entries (older than 1 hour)
        current_time = datetime.now()
        self.sent_alerts = {
            k: v for k, v in self.sent_alerts.items()
            if (current_time - v).total_seconds() < 1800
        }
    
    def send_alert_email(self, alert_data):
        """Send email alert"""
        if not self.alert_recipients:
            logger.warning("No alert recipients configured")
            return False
        
        try:
            subject = f"🚨 UCM6202 Queue Alert: {alert_data['type']} ({alert_data['severity']})"
            
            # Create email body
            email_body = self.create_alert_email_body(alert_data)
            
            # Send email
            send_mail(
                subject=subject,
                message=email_body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@yourcompany.com'),
                recipient_list=self.alert_recipients,
                fail_silently=False,
            )
            
            logger.info(f"Alert email sent: {alert_data['type']} for caller {alert_data['caller_number']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {str(e)}")
            return False
    
    def create_alert_email_body(self, alert_data):
        """Create formatted email body"""
        severity_emoji = "🔴" if alert_data['severity'] == 'CRITICAL' else "🟡"
        
        email_body = f"""
{severity_emoji} UCM6202 Call Queue Alert

Alert Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Alert Type: {alert_data['type']}
• Severity: {alert_data['severity']}
• Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Call Information:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Queue: {alert_data['queue_name']}
• Queue Chairman: {alert_data['queuechairman']}
• Caller Number: {alert_data['caller_number']}
• Wait Time: {alert_data['wait_time_display']} ({alert_data['wait_time_seconds']} seconds)
• Call Start: {alert_data['start_time']}
• Assigned Agent: {alert_data['agent']}
• Extension: {alert_data.get('extension', 'N/A')}

Action Required:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if alert_data['type'] == 'UNANSWERED_CALL':
            email_body += "⚠️  CRITICAL: This call has exceeded the maximum wait time and remains unanswered!\n"
            email_body += "   Please check the queue immediately and ensure agents are available.\n\n"
        else:
            email_body += "⚠️  WARNING: This call is experiencing a long wait time.\n"
            email_body += "   Please monitor the queue and consider reassigning agents.\n\n"
        
        email_body += f"Dashboard Link: {getattr(settings, 'BASE_URL', 'http://localhost:8000')}\n\n"
        email_body += "This is an automated alert from the UCM6202 Call Queue Monitoring System.\n"
        email_body += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        return email_body.strip()

# Global alert manager instance
alert_manager = CallAlertManager()







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
    """Enhanced view with integrated alert monitoring"""
    
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
        
        # Clean input data
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
                return redirect('agent_search')
                
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
            
            # *** NEW: Check for alerts before filtering ***
            queue_name = f"Queue {que}" if que != 'all' else "All Queues"
            alerts = alert_manager.check_queue_for_alerts(queue_data, queue_name)
            
            # Send alert emails if needed
            for alert in alerts:
                alert_manager.send_alert_email(alert)
            
            # Filter data based on connection status
            filtered_data = self.filter_data(queue_data, con)
            
            context = {
                'agent_data': filtered_data,
                'search_params': {
                    'sta': sta, 'end': end, 'que': que, 'age': age, 'con': con
                },
                'reload_needed': False,
                'current_alerts': alerts,  # Pass alerts to template
                'alerts_count': len(alerts)
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
            
            response = session.post(
                api_url,
                json=queue_request,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            
            # Check if reload is needed
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




class LoginSearchView(View):
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
        return render(request, 'queuestat/login_search.html', context)



class LoginDetailsView(View):
    """Enhanced view with integrated alert monitoring"""
    
    def post(self, request):
        # Validate form data
        sta = request.POST.get('sta')
        end = request.POST.get('end')
        que = request.POST.get('que')
        age = request.POST.get('age')
        
        
        # Check if required fields are present
        if not all([sta, end]) or que is None or age is None :
            messages.error(request, 'Missing Entry!')
            return redirect('login_search')
        
        # Clean input data
        sta = self.clean_input(sta)
        end = self.clean_input(end)
        que = self.clean_input(que) 
        age = self.clean_input(age)
        
        
        try:
            # Get API data
            cookie = self.get_api_cookie()
            if not cookie:
                messages.error(request, 'Failed to authenticate with API')
                return redirect('queuestats:login_search')
                
            # Get queue statistics
            queue_data = self.get_queue_data(cookie, sta, end, que, age)
            
            if not queue_data:
                context = {
                    'reload_needed': True,
                    'search_params': {
                        'sta': sta, 'end': end, 'que': que, 'age': age
                    }
                }
                return render(request, 'queuestat/login_details.html', context)
            
           
            # Filter data based on connection status
            filtered_data = self.filter_data(queue_data)
            
            context = {
                'agent_data': filtered_data,
                'search_params': {
                    'sta': sta, 'end': end, 'que': que, 'age': age
                },
                'reload_needed': False,
                
            }
            return render(request, 'queuestat/login_details.html', context)
            
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('queuestats:login_search')
    
    def clean_input(self, data):
        """Equivalent to PHP test_input function"""
        if data is None:
            return ''
        data = str(data).strip().strip('/')
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
                    "statisticsType": "loginhistory",
                    "cookie": cookie
                }
            }
            
            headers = {
                "Connection": "close",
                "Content-Type": "application/json"
            }
            
            response = session.post(
                api_url,
                json=queue_request,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            
            # Check if reload is needed
            if isinstance(data.get('status'), int):
                return None
                
            return data.get('queue_statistics', [])
            
        except Exception as e:
            print(f"Queue data error: {e}")
            return None
    
    def filter_data(self, queue_data):
        """Filter data based on connection status"""
        filtered_results = []
        
        for item in queue_data:
            agent_data = item.get('agent', {})
            
            # Skip entries where agent is "NONE"
            if agent_data.get('agent') == 'NONE':
                continue
                
           
            
            filtered_results.append(agent_data)
        
        return filtered_results












# Additional helper function for testing
def test_realtime_data(request):
    """Test endpoint to check what data we're getting from the API"""
    try:
        now = datetime.now()
        start_time = now.strftime('%Y-%m-%d' )
        end_time = now.strftime('%Y-%m-%d' )
        
        # Initialize alerts list at the beginning
        alerts = []
        
        # Get API cookie
        agent_view = AgentDetailsView()
        cookie = agent_view.get_api_cookie()
        
        if not cookie:
            return HttpResponse("❌ Failed to get API cookie")
        
        # Get queue data
        queue_data = agent_view.get_queue_data(cookie, start_time, end_time, '', '')
        
        output = []
        output.append("=== Real-time Data Test ===")
        output.append(f"Time range: {start_time} to {end_time}")
        output.append(f"API cookie: {cookie[:20]}...")
        output.append(f"Queue data type: {type(queue_data)}")
        output.append(f"Queue data length: {len(queue_data) if queue_data else 'None'}")
        
        if queue_data:
            # Check for alerts FIRST - on ALL queue data, not just first 3
            alerts = alert_manager.check_queue_for_alerts(queue_data, "Real-time Monitor")
            output.append(f"Alerts found: {len(alerts)}")
            
            output.append("\n--- Sample Records ---")
            for i, record in enumerate(queue_data[:3]):  # Show first 3 records
                output.append(f"\nRecord {i+1}:")
                output.append(json.dumps(record, indent=2))
                
                # Check for alert conditions (just for display purposes)
                agent_data = record.get('agent', {})
                if agent_data.get('agent') != 'NONE':
                    caller_num = agent_data.get('callernum', 'Unknown')
                    connect_status = agent_data.get('connect', 'unknown')
                    wait_time = agent_data.get('wait_time', '0')
                    
                    output.append(f"  -> Caller: {caller_num}")
                    output.append(f"  -> Connected: {connect_status}")
                    output.append(f"  -> Wait time: {wait_time}")
                    
                    # Parse wait time
                    wait_seconds = alert_manager.parse_wait_time(wait_time)
                    output.append(f"  -> Wait seconds: {wait_seconds}")
                    
                    if connect_status == 'no' and wait_seconds > 5:
                        output.append(f"  -> ⚠️ Would trigger alert!")
            
            # Send email alerts (now alerts is always defined and contains all alerts)
            output.append(f"\n--- Sending {len(alerts)} Alerts ---")
            for i, alert in enumerate(alerts):
                try:
                    output.append(f"Sending alert {i+1}: {alert.get('type', 'Unknown')} for {alert.get('caller_number', 'Unknown')}")
                    alert_manager.send_alert_email(alert)
                    logger.info(f"Alert sent: {alert['type']} for {alert['caller_number']}")
                    output.append(f"  ✅ Alert {i+1} sent successfully")
                except Exception as email_error:
                    logger.error(f"Failed to send alert email: {email_error}")
                    output.append(f"  ❌ Alert {i+1} failed: {email_error}")
            
            # Count waiting calls (connect = 'no')
            waiting_calls = 0
            connected_calls = 0
            
            for item in queue_data:
                agent_data = item.get('agent', {})
                if agent_data.get('agent') != 'NONE':
                    if agent_data.get('connect') == 'no':
                        waiting_calls += 1
                    elif agent_data.get('connect') == 'yes':
                        connected_calls += 1
            
            # Return detailed status
            return JsonResponse({
                'status': 'success',
                'timestamp': now.isoformat(),
                'alerts_count': len(alerts),
                'alerts': alerts,
                'total_calls': len(queue_data),
                'waiting_calls': waiting_calls,
                'connected_calls': connected_calls,
                'monitoring_period': f"{start_time} to {end_time}",
                'debug_info': {
                    'api_cookie_length': len(cookie) if cookie else 0,
                    'first_record_keys': list(queue_data[0].keys()) if queue_data else [],
                    'sample_agent_data': queue_data[0].get('agent', {}) if queue_data else {}
                }
            })

        else:
            output.append("\n❌ No queue data returned")
        
        return HttpResponse("<pre>" + "\n".join(output) + "</pre>")
        
    except Exception as e:
        import traceback
        return HttpResponse(f"❌ Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}")









"""
Add these settings to your Django settings.py:

# Call Alert Settings
CALL_WAIT_WARNING_SECONDS = 30      # Send warning after 30 seconds
CALL_WAIT_CRITICAL_SECONDS = 60     # Send critical alert after 60 seconds  
CALL_UNANSWERED_SECONDS = 90        # Consider call unanswered after 90 seconds

# Email settings for alerts
CALL_ALERT_RECIPIENTS = [
    'supervisor@yourcompany.com',
    'manager@yourcompany.com',
    'admin@yourcompany.com',
]

# Email backend configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # or your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'UCM6202 Alert System <alerts@yourcompany.com>'

# Optional: Base URL for dashboard links in emails
BASE_URL = 'https://yourdomain.com'
"""

# import asyncio
# from django.http import HttpResponse
# from asgiref.sync import sync_to_async

# async def start_continuous_monitoring(request):
#     """Start continuous monitoring (runs in background)"""
    
#     async def monitor_loop():
#         while True:
#             try:
#                 # Run the monitoring check
#                 await sync_to_async(check_queue_sync)()
#                 await asyncio.sleep(30)  # Wait 30 seconds
#             except Exception as e:
#                 logger.error(f"Async monitor error: {e}")
#                 await asyncio.sleep(30)
    
#     # Start the monitoring task
#     asyncio.create_task(monitor_loop())
    
#     return HttpResponse("✅ Continuous monitoring started! Check logs for activity.")

# def check_queue_sync():
#     try:
#         now = datetime.now()
#         start_time = now.strftime('%Y-%m-%d' )
#         end_time = now.strftime('%Y-%m-%d' )
        
#         # Get API cookie
#         agent_view = AgentDetailsView()
#         cookie = agent_view.get_api_cookie()
        
#         if not cookie:
#             return HttpResponse("❌ Failed to get API cookie")
        
#         # Get queue data
#         queue_data = agent_view.get_queue_data(cookie, start_time, end_time, '', '')
        
#         output = []
#         output.append("=== Real-time Data Test ===")
#         output.append(f"Time range: {start_time} to {end_time}")
#         output.append(f"API cookie: {cookie[:20]}...")
#         output.append(f"Queue data type: {type(queue_data)}")
#         output.append(f"Queue data length: {len(queue_data) if queue_data else 'None'}")
        
        
        
        
        
#         if queue_data:
#             output.append("\n--- Sample Records ---")
#             for i, record in enumerate(queue_data[:3]):  # Show first 3 records
#                 output.append(f"\nRecord {i+1}:")
#                 output.append(json.dumps(record, indent=2))
                
#                 # Check for alert conditions
#                 agent_data = record.get('agent', {})
#                 if agent_data.get('agent') != 'NONE':
#                     caller_num = agent_data.get('callernum', 'Unknown')
#                     connect_status = agent_data.get('connect', 'unknown')
#                     wait_time = agent_data.get('wait_time', '0')
                    
#                     output.append(f"  -> Caller: {caller_num}")
#                     output.append(f"  -> Connected: {connect_status}")
#                     output.append(f"  -> Wait time: {wait_time}")
                    
#                     # Parse wait time
#                     wait_seconds = alert_manager.parse_wait_time(wait_time)
#                     output.append(f"  -> Wait seconds: {wait_seconds}")
                    
#                     if connect_status == 'no' and wait_seconds > 30:
#                         output.append(f"  -> ⚠️ Would trigger alert!")
#                         # Check for alerts
#                         alerts = alert_manager.check_queue_for_alerts(queue_data, "Real-time Monitor")
            
#             # Send email alerts
#             for alert in alerts:
#                 try:
#                     alert_manager.send_alert_email(alert)
#                     logger.info(f"Alert sent: {alert['type']} for {alert['caller_number']}")
#                 except Exception as email_error:
#                     logger.error(f"Failed to send alert email: {email_error}")
            
#             # Count waiting calls (connect = 'no')
#             waiting_calls = 0
#             connected_calls = 0
            
#             for item in queue_data:
#                 agent_data = item.get('agent', {})
#                 if agent_data.get('agent') != 'NONE':
#                     if agent_data.get('connect') == 'no':
#                         waiting_calls += 1
#                     elif agent_data.get('connect') == 'yes':
#                         connected_calls += 1
            
#             # Return detailed status
#             return JsonResponse({
#                 'status': 'success',
#                 'timestamp': now.isoformat(),
#                 'alerts_count': len(alerts),
#                 'alerts': alerts,
#                 'total_calls': len(queue_data),
#                 'waiting_calls': waiting_calls,
#                 'connected_calls': connected_calls,
#                 'monitoring_period': f"{start_time} to {end_time}",
#                 'debug_info': {
#                     'api_cookie_length': len(cookie) if cookie else 0,
#                     'first_record_keys': list(queue_data[0].keys()) if queue_data else [],
#                     'sample_agent_data': queue_data[0].get('agent', {}) if queue_data else {}
#                 }
#             })

#         else:
#             output.append("\n❌ No queue data returned")
        
#         return HttpResponse("<pre>" + "\n".join(output) + "</pre>")
        
#     except Exception as e:
#         import traceback
#         return HttpResponse(f"❌ Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}")
