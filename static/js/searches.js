$(document).ready(function() {
	var opts = { lines: 7, length: 17, width: 16, radius: 29, corners: 0.6, rotate: 0, color: '#000', speed: 1, trail: 60,
		     shadow: false, hwaccel: false, className: 'spinner', zIndex: 2e9, top: $(document).height()*0.35, left: $(document).width()*0.45};
	var target = document.getElementsByTagName("body")[0];
	var spinner = new Spinner(opts).spin(target);
	spinner.stop();
	$("#search-form").submit(function() {
		$("#slider-input").attr("value", $("#slider").slider("value"));
		var formData = $("#search-form").serialize();
		$("#search-container").html("");
		spinner.spin(target);
		$.ajax({
			type: "POST",
			    url: "/ajax/quick-search",
			    data: formData,
			    success: function(data) { 
			    spinner.stop(); 
			    $("#search-container").html(data);
			},
			    error: function(data) {
			    alert("Your search was not successful.");
			}
		    });
		return false;
	    });
	    
	$( "#slider" ).slider({
		value:3,
		    min: 1,
		    max: 5,
		    step: 1,
		    slide: function( event, ui ) {
		    $( "#amount" ).val( "$" + ui.value );
		}
	    });
	$( "#amount" ).val( "$" + $( "#slider" ).slider( "value" ) );
	
	$( "#budgetslider" ).slider({
		value:3,
		    min: 1,
		    max: 5,
		    step: 1,
		    slide: function( event, ui ) {
		    $( "#amount" ).val( "$" + ui.value );
		}
	    });
	$( "#amount" ).val( "$" + $( "#budgetslider" ).slider( "value" ) );
	
	$( "#distanceslider" ).slider({
		value:3,
		    min: 1,
		    max: 5,
		    step: 1,
		    slide: function( event, ui ) {
		    $( "#amount" ).val( "$" + ui.value );
		}
	    });
	$( "#amount" ).val( "$" + $( "#distanceslider" ).slider( "value" ) );
	
    });