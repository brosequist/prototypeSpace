function checkName(str) {
  

  var ajax;
  
  // don't do anything if the string is zero characters
  if (str.length == 0) {
    document.getElementByID("namecheck").innerHTML = ""
    return;
  }

  // create new AJAX object
  ajax = new XMLHttpRequest();
  
  // run a get for name check info when readystatechange occurs
  ajax.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      document.getElementByID("namecheck").innerHTML = this.responseText;
    }
  };
  
  // run a JQuery request against the check function in application.py
  ajax.open("GET", "/check?username=" + str, true);
  ajax.send();

}
