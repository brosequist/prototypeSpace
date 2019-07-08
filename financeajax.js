$(function checkName()
{
  // create new AJAX object
  var ajax = new XMLHttpRequest();
  
  ajax.onreadystatechange = function() {
  if (aj.readyState == 4 && aj.status == 200) {
        $('#usernamecheck').html(ajax.responseText);
  };
    
  ajax.open("GET", username + '.html', true);
  ajax.send();
  ajax.get();

  $('buttonnamehere').bind('click', function() {
    $.getJSON('/check',function(data) {
      //do nothing
    });
    
  });
});
