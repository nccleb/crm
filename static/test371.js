function prev(){
     
show();
  }



function on(){
  y=setInterval("prev()",1000);
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
      document.getElementById("ap").value = this.responseText;
     
    }
  };
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
      document.getElementById("aq").value = this.responseText;
     
    }
  };
xhttp.open("GET", $("#id2").load(location.href + " #id2") , true);
  xhttp.send();
}
