function prev(){
    show();
    
}

function on(){
    y = setInterval("prev()", 1000);
}

function on2(){
    y = setInterval("startQueueMonitoring()", 1000);
}

function show() {
    var xhttp;
    
    if (window.XMLHttpRequest) {
        // code for modern browsers
        xhttp = new XMLHttpRequest();
    } else {
        // code for IE6, IE5
        xhttp = new ActiveXObject("Microsoft.XMLHTTP");
    }
    
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            try {
                // Parse the JSON response
                var response = JSON.parse(this.responseText);
                
                // Update the display element
                var element = document.getElementById("ap");
                if (element) {
                    if (response.status === 'success') {
                        element.value = response.display_value;
                        
                        // Optional: Show notification for new calls
                        if (response.is_new) {
                            console.log('New call from: ' + response.caller_id);
                            
                            // You can add visual/audio notification here
                            // For example, change background color temporarily
                            element.style.backgroundColor = '#ffff99';
                            setTimeout(function() {
                                element.style.backgroundColor = '';
                            }, 2000);
                        }
                    } else {
                        // File is empty or error - just clear the field, don't show error
                        element.value = '';
                    }
                }
            } catch (e) {
                console.error('Error parsing caller ID response:', e);
            }
        }
    };
    
    // Call the new API endpoint instead of reloading the page
    //xhttp.open("GET", "/getfirstline/", true);
    xhttp.open("GET", $("#id").load(location.href + " #id") , true);
    xhttp.send();
}

function show2() {
    var xhttp;
    
    if (window.XMLHttpRequest) {
        // code for modern browsers
        xhttp = new XMLHttpRequest();
    } else {
        // code for IE6, IE5
        xhttp = new ActiveXObject("Microsoft.XMLHTTP");
    }
    
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            try {
                var response = JSON.parse(this.responseText);
                var element = document.getElementById("aq");
                if (element) {
                    if (response.status === 'success') {
                        element.value = response.display_value;
                    } else {
                        element.value = '';
                    }
                }
            } catch (e) {
                console.error('Error parsing caller ID response:', e);
            }
        }
    };
    
    xhttp.open("GET", "queue/test/", true);
    xhttp.send();
}

// Optional: Function to manually check for calls and show messages
function manualRefresh() {
    window.location.href = '/get-caller-id/';
}

// Optional: Function to clear caller ID
function clearCallerID() {
    window.location.href = '/clear-caller-id/';
}





// Simple 30-second monitoring
let monitoringActive = false;
let monitorInterval = null;

function startQueueMonitoring() {
    if (monitoringActive) return;
    
    monitoringActive = true;
    console.log('✅ Queue monitoring started');
    
    // Run initial check
    checkQueue();
    
    // Set up 30-second interval
    monitorInterval = setInterval(checkQueue, 30000);
}

function stopQueueMonitoring() {
    monitoringActive = false;
    if (monitorInterval) {
        clearInterval(monitorInterval);
        monitorInterval = null;
    }
    console.log('⏹️ Queue monitoring stopped');
}

async function checkQueue() {
    try {
        console.log('🔍 Checking queue...');
        
        const response = await fetch('/queue/test/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log('📊 Queue data:', data);
        
        // Handle alerts
        if (data.alerts && data.alerts.length > 0) {
            console.log('🚨 ALERTS DETECTED:', data.alerts);
            // You can add custom alert handling here
        }
        
    } catch (error) {
        console.error('❌ Queue check error:', error);
    }
}

// Start monitoring automatically
startQueueMonitoring();