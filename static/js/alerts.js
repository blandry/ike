$(document).ready(function() {
	var alertText = $("#alert").attr("text");
	if (alertText!=""){
	    var alertType = $("#alert").attr("type");
	    var alertHeader = $("#alert").attr("header");
	    var alertStyle = "position: absolute; width: 50%; left: 23%; top: 30px; text-align: center;";
	    var alertHtml = "<div id='alert' class='alert "+alertType+" hide' style='"+alertStyle+"'><button type='button' class='close' data-dismiss='alert'>&times;</button>";
	    alertHtml += "<strong>"+alertHeader+"</strong> "+alertText+"</div>";
	    $("#alert").replaceWith(alertHtml);
	    $("#alert").fadeIn(600);
	};
    });