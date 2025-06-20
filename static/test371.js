function prev(){
    show();
}

function on(){
    y = setInterval("prev()", 1000);
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
    
    xhttp.open("GET", "getfirstline/", true);
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