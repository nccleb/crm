import datetime
import os
import logging
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.views import LogoutView
from django.contrib.auth import logout
from client.models import Client

# Set up logging
logger = logging.getLogger(__name__)


class UserLogoutView(LogoutView):
    def get(self, request):
        logout(request)
        return redirect('login')


def index(request):
    return render(request, 'core/index.html')

def on(request):
    return render(request, 'core/on.html')

def off(request):
    return render(request, 'core/off.html')

def about(request):
    return render(request, 'core/about.html')


def getfirstline(request):
    """
    Ultra-simplified version - just reads the last line without any complex extraction
    """
    today = datetime.date.today()
    month = today.month
    year = today.year
    
    # Use the exact path from your original code
    path = r"C:\Users\user\crm\django_env\tealcrm\callerid\callerid.txt"
    
    try:
        # Check if file exists
        # if not os.path.exists(path):
        #     logger.error(f"File not found: {path}")
        #     messages.error(request, f'Caller ID file not found!')
        #     return render(request, 'core/about.html', {
        #         'messages': ['Caller ID file not found!'],
        #         'years': year,
        #         'months': month,
        #     })
        
        # # Check if file is empty
        # if os.path.getsize(path) == 0:
        #     logger.error(f"File is empty: {path}")
        #     #messages.warning(request, 'Caller ID file is empty!')
        #     return render(request, 'core/about.html', {
        #         'messages': ['Caller ID file is empty!'],
        #         'years': year,
        #         'months': month,
        #     })
        
        # Read the file
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
            # if not lines:
            #     logger.warning("No lines found in file")
            #     messages.info(request, 'No calls as of yet!')
            #     return render(request, 'core/about.html', {
            #         'messages': ['No calls as of yet!'],
            #         'years': year,
            #         'months': month,
            #     })
            
            # Get the last line and clean it up
            last_line = lines[-1].strip()
            logger.info(f"Successfully read last line: '{last_line}'")
            
            # if not last_line:
            #     logger.warning("Last line is empty")
            #     messages.info(request, 'No recent calls found!')
            #     return render(request, 'core/about.html', {
            #         'messages': ['No recent calls found!'],
            #         'years': year,
            #         'months': month,
            #     })
            
            # Store the entire line in session (no extraction)
            request.session['idempresa'] = last_line
            
            # Get clients
            clients = Client.objects.all()
            
            # Success - show the caller info
            #messages.success(request, f'Latest caller: {last_line}')
            last_line = last_line[0:4]
            return render(request, 'core/about.html', {
                'cliens': last_line,  # Full caller line
                'years': year,
                'months': month,
                'numbers': clients,
            })
            
   
    
       
    
        
    except Exception as e:
        #error_msg = f'Unexpected error reading caller ID file: {str(e)}'
        #logger.error(error_msg)
       # messages.error(request, 'Error reading caller ID file!')
        return render(request, 'core/about.html', {
            #'messages': ['Error reading caller ID file!'],
            #'years': year,
            #'months': month,
        })


def test_file_access(request):
    """
    Simple test function to check file access
    """
    path = r"C:\Users\user\crm\django_env\tealcrm\callerid\callerid.txt"
    
    test_results = {
        'file_path': path,
        'exists': os.path.exists(path),
        'is_file': os.path.isfile(path) if os.path.exists(path) else False,
        'size': os.path.getsize(path) if os.path.exists(path) else 0,
        'readable': False,
        'content_preview': [],
        'error': None
    }
    
    if test_results['exists']:
        try:
            # Test if we can read the file
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                test_results['readable'] = True
                
                # Get last few lines for preview
                lines = content.splitlines()
                test_results['content_preview'] = lines[-5:] if len(lines) >= 5 else lines
                test_results['total_lines'] = len(lines)
                
        except Exception as e:
            test_results['error'] = str(e)
    
    return render(request, 'core/test_results.html', {
        'test_results': test_results,
        'today': datetime.date.today(),
    })


# Alternative function that tries multiple common file paths
def getfirstline_auto_detect(request):
    """
    Try multiple possible file paths automatically
    """
    today = datetime.date.today()
    month = today.month
    year = today.year
    
    # List of possible file paths to try
    possible_paths = [
        r"C:\Users\user\crm\django_env\tealcrm\callerid\callerid.txt",
        r"C:\Users\user\crm\django_env\tealcrm\callerID2025-19.txt",
        r"C:\Mdr\CallerID\callerid.txt",
        r"C:\CallerID\callerid.txt",
        r".\callerid.txt",  # Current directory
        r"callerid.txt",    # Just filename
    ]
    
    for path in possible_paths:
        try:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        if last_line:  # Make sure it's not empty
                            request.session['idempresa'] = last_line
                            clients = Client.objects.all()
                            
                            messages.success(request, f'Found caller ID file at: {path}')
                            messages.info(request, f'Latest caller: {last_line}')
                            
                            return render(request, 'core/about.html', {
                                'cliens': last_line,
                                'years': year,
                                'months': month,
                                'numbers': clients,
                                'file_path_used': path,  # For debugging
                            })
        except Exception as e:
            logger.warning(f"Failed to read {path}: {e}")
            continue
    
    # If we get here, no file was found
    messages.error(request, 'No caller ID file found in any expected location!')
    logger.error("No caller ID file found in any of the expected locations")
    
    return render(request, 'core/about.html', {
        'messages': ['No caller ID file found!'],
        'years': year,
        'months': month,
        'searched_paths': possible_paths,  # For debugging
    })