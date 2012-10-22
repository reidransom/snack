var qt_rate = 100;
//drift is 3.60 seconds per hour

var isDebugging = false;
function ErrorSetting(msg, file_loc, line_no) {
    
    
    var e_msg=msg;
    var e_file=file_loc;
    var e_line=line_no;
    var error_d = "Error in file: " + file_loc +
                          "\nline number:" + line_no +
                           "\nMessage:" + msg;
    if(isDebugging)
        alert("Error Found !!!\n--------------\n"+error_d);

     return true;
}
//window.onerror = ErrorSetting;

var initSwitch = function() {
	$$('.switch').each( function(elem) {
		var id = elem.identify();
		var status = new Array();
		status = elem.readAttribute('status').split(' ');
		$$('[switch='+id+']').each( function(e) {
			e.addClassName(status[0]);
		});
		elem.observe('click', function() {
			var id = elem.identify();
			var status = new Array();
			status = elem.readAttribute('status').split(' ');
			$$('[switch='+id+']').each( function(e) {
				if (e.hasClassName(status[0])) {
					status = [status[1], status[0]];
				}
				e.removeClassName(status[1]);
				e.addClassName(status[0]);
			});
			session_set(id, status[0]+' '+status[1]);
		});
	});
}

Element.addMethods({
	get_qtplayer: function(element) {
		var player = element.select('embed')[0];
		if (!player) {
			var player = element.select('object')[0];
		}
		return player;
	},
	getQtRectangle: function(element) {
		var rect = Try.these(
			function() { return element.GetRectangle() }
		) || false;
		if (!rect) return rect;
		return rect.split(',').map(function(s) { return s*1; });
	},
	getQtMatrix: function(element) {
		var matrix = Try.these(
			function() { return element.GetMatrix() }
		) || false;
		if (!matrix) return matrix;
		return matrix.split('\r').map(function(row) { return row.split(',').map(function(s) { return s*1; }) });
	},
	setWidth: function(element, width) {
		element.setStyle({width:width});
	},
	setHeight: function(element, height) {
		element.setStyle({height:height});
	},
	display_none: function(element) {
		element.setStyle({display:'none'});
	},
	display_inline: function(element) {
		element.setStyle({display:'inline'});
	},
	display_block: function(element) {
		element.setStyle({display:'block'});
	},
	selectFirst: function(element, selector) {
		return Try.these(
			function() { return $(element).select(selector)[0]; }
		) || false;
	},
	insertAtCursor: function(element, text) {
		return edInsertContent($(element), text);
	},
	rewind: function(element) {
		var rate = $(element).getRate();
		if (rate >= 0) {
			rate = -1;
		}
		else {
			rate = rate * 2;
		}
		$(element).SetRate(rate);
	},
	forward: function(element) {
		var rate = $(element).getRate();
		if (rate <= 0) {
			rate = 1;
		}
		else {
			rate = rate * 2;
		}
		$(element).SetRate(rate);
	},
	playpause: function(element) {
		if ($(element).getRate() == 0) {
			$(element).SetRate(1);
		}
		else {
			$(element).SetRate(0);
		}
	},
	getRate: function(element) {
		return Try.these(
			function () { return element.GetRate(); }
		) || 0;
	},
	getEndTime: function(element) {
		return Try.these(
			function () { return element.GetEndTime() / 1.001; }
		) || 0;
	},
	getOffset: function(element) {
		return Try.these(
			function () {
				// taking the modulus of getEndTime ensures that the time returned is less than
				// the duration of the movie (this happens if the movie is looped ( i think ;) )).
				var qtoffset = element.GetTime() % element.GetEndTime();
				
				// Find the offset if for whatever reason qtoffset happens to be negatory
				if (qtoffset < 0) {
					qtoffset = element.GetEndTime() + qtoffset;
				}
				
				// This is a correction for videos that have 29.97 frame rate
				// todo: I should do a couple more tests with videos from drop frame sequences and videos
				// from non-drop sequences.
				qtoffset = qtoffset / 1.001;

				// Multiply by fps and divide by timescale
				qtoffset = qtoffset * qt_rate / element.GetTimeScale();
				
				return Math.floor(qtoffset);
			}
		) || 0;
	},
	setOffset: function(element, offset) {
		return Try.these(
			function () {
				//element.SetTime(offset * 1.001);
				offset = (offset * 1.001 * element.GetTimeScale()) / qt_rate;
				element.SetTime(offset);
				return; 
			}
		) || 0;
	},
	getTimeScale: function(element) {
		return Try.these(
			function () { return element.GetTimeScale(); }
		) || 600;
	}
});

var tc_prev_length = {};
var validateTC = function() {
	
	// arguments
	var tc_input = $(arguments[0]);
	var frame_rate = (arguments[1]) ? arguments[1] : '30ND';
	var event_name = (arguments[2]) ? arguments[2] : 'submit';
	
	// variables
	var d = (frame_rate == '30DF') ? ';' : ':';
	if ( (frame_rate == '30DF') || (frame_rate == '30ND') ) {
		frame_rate = '30';
	}
	frame_rate = parseInt(frame_rate);

	var id = tc_input.identify();
	
	// massage
	var tc = $F(tc_input).gsub(/[:;]/, d).gsub(/[^:;\d]/, '');
	var h=0; var m=0; var s=0; var f=0;
	if (tc.match(/^\d\d/)) {
		h = tc.substring(0,2)%24;
		tc = h.toPaddedString(2) + tc.substring(2);
	}
	if (tc.match(/^\d\d[:;]\d\d/)) {
		m = tc.substring(3,5)%60;
		tc = tc.substring(0,3) + m.toPaddedString(2) + tc.substring(5);
	}
	if (tc.match(/^\d\d[:;]\d\d[:;]\d\d/)) {
		s = tc.substring(6,8)%60;
		tc = tc.substring(0,6) + s.toPaddedString(2) + tc.substring(8);
	}
	if (tc.match(/^\d\d[:;]\d\d[:;]\d\d[:;]\d\d/)) {
		f = tc.substring(9,11)%frame_rate;
		if ((d==";") && (s==0) && (m%10!=0) && (f<2)) f = 2;
		tc = tc.substring(0,9) + f.toPaddedString(2);
	}
	tc_input.value = tc;
	
	// auto complete
	if ((tc_prev_length[id]+1 == tc.length) && ([2,5,8].indexOf(tc.length) != -1)) {
		tc_input.insertAtCursor(d);
	}
	tc_prev_length[id] = tc.length;
	
	// validate
	var regexArray = ['[0-9]','[0-9]','[;:]','[0-9]','[0-9]','[;:]','[0-9]','[0-9]','[;:]','[0-9]','[0-9]'];
	var re = new RegExp('^'+regexArray.slice(0, tc.length).join(''));
	var v = tc.match(re);
	if ( (event_name!='keyup') && (tc.length!=11) ) v = false;
	if ( (event_name=='load') && (tc.length==0) ) v = true;
	if (tc == '') v = true;
	if (v) {
		//$(id+'_help').hide();
	}
	else {
		//$(id+'_help').show();
	}
}

/* 
	This function takes 3 arguments at most:
	tc_input : should be the element or element id of a timecode (textbox input)
	frame_rate_input : should be the input element of the frame_rate
	initial_value : should be the inital value of the tc_input
*/
var initTCInput = function() {
	var tc_input = $(arguments[0]);
	var frame_rate_select = $(arguments[1]);
	
	var initial_value = (arguments[2]) ? arguments[2] : "";
	
	var id = tc_input.identify();
	tc_prev_length[id] = $F(tc_input).length;
	
	validateTC(tc_input, $F(frame_rate_select), 'load');
	tc_input.observe('keyup', function() { validateTC(tc_input, $F(frame_rate_select), 'keyup'); });
	tc_input.observe('blur', function() { validateTC(tc_input, $F(frame_rate_select), 'blur'); });
	if (frame_rate_select) {
		frame_rate_select.observe('change', function() { validateTC(tc_input, $F(frame_rate_select), 'change'); });
	}
}

var initDisplaySize = function() {
	var display_size_change = function() {
		var f = ($F('display_size') == 'custom') ? Element.show : Element.hide;
		f($('custom_size'));
	}
	display_size_change();
	$('display_size').observe('change', display_size_change);
}

// calling the function
// insertAtCursor(document.formName.fieldName, 'this value');
function str_to_fc(s) {
	return tc_to_fc(str_to_tc(s));
}

function fc_to_str(fc) {
	var fc = arguments[0];
	var delim = (arguments[1]) ? arguments[1] : start_tc.charAt(2);
	return tc_to_str(fc_to_tc(fc), delim);
}

function str_to_tc(s) {
	var delim = Try.these(
		function() { return s.charAt(2) },
		function() { alert('badtc: '+s); return start_tc.charAt(2) }
	) || ':';
	tc = s.split(delim);
	return [tc[0]*1, tc[1]*1, tc[2]*1, tc[3]*1];
}

var offsetFromTc = function(tc) {
	return Try.these(
		function() {
			// find the current edit in the edl
			var i = 0;
			while ( !( (tc >= edl[i]['srcin']) && (tc < edl[i]['srcout']) ) ) {
				i = i + 1;
				if (i > edl.length) return false;
			}
			var offset = str_to_fc(edl[i]['seqin']) + str_to_fc(tc) - str_to_fc(edl[i]['srcin']) - str_to_fc(edl[0]['seqin']);
			if (offset < 0) offset += tc_to_fc([24,0,0,0]);
			return offset+'';
		},
		function() {
			var offset = str_to_fc(tc) - str_to_fc(start_tc);
			if (offset < 0) offset += tc_to_fc([24,0,0,0]);
			return offset+'';
		}
	) || false;
}

function new_str_to_offset(tc) {
	
	return Try.these(
		function() {
			// find the current edit in the edl
			var i = 0;
			while ( !( (tc >= edl[i]['srcin']) && (tc < edl[i]['srcout']) ) ) {
				i = i + 1;
				if (i > edl.length) return false;
			}
			var offset = str_to_fc(edl[i]['seqin']) + str_to_fc(tc) - str_to_fc(edl[i]['srcin']) - str_to_fc(edl[0]['seqin']);
			if (offset < 0) offset += tc_to_fc([24,0,0,0]);
			return offset+'';
		},
		function() {
			var offset = str_to_fc(tc) - str_to_fc(start_tc);
			if (offset < 0) offset += tc_to_fc([24,0,0,0]);
			return offset+'';
		}
	) || false;
}

var get_fps = function() {
	if ( (frame_rate == '30ND') || (frame_rate == '30DF') ) {
		return 30;
	}
	return parseInt(frame_rate);
}
var get_delim = function() {
	if (frame_rate == '30DF') {
		return ';';
	}
	return ":";
}

function tc_to_fc(tc) {
	var fps = get_fps();
	return 3600*fps*tc[0] + 60*fps*tc[1] + fps*tc[2] + tc[3];
}

function fc_to_tc(fc) {
	var fps = get_fps();
	fc = parseInt(fc);
	return [
		Math.floor(fc/(3600*fps))%24,
		Math.floor((fc%(3600*fps))/(60*fps)),
		Math.floor((fc%(60*fps))/fps),
		Math.floor(fc%fps)
	];
}

function zeropad(n) { return (n<10) ? '0'+n : ''+n; }

function is_qt_plugin_ready(qt_obj) {
	return true;
	qt_obj = $(qt_obj);
	pluginstatus = qt_obj.GetPluginStatus();
	return ( (pluginstatus == "Playable") || (pluginstatus == "Complete") );
}

function display_timecode(replace_elem, qt_elem, start_tc) {
	
	offset = $(qt_elem).getOffset();
	tc = qt_to_tc(offset, start_tc);
	
	f = ($(qt_elem).getRate() == 0) ? zeropad(tc[3]) : '--';
	var delim = start_tc.charAt(2);
	tc = zeropad(tc[0])+delim+zeropad(tc[1])+delim+zeropad(tc[2])+delim+f;
	if (tc != $(replace_elem).innerHTML) {
		$(replace_elem).update(tc);
	}
	return;
}

function display_source_tc(replace, qt_elem, edl) {
	
	var tc = qt_to_tc( $(qt_elem).getOffset(), edl[0]['seqin'] );
	var delim = edl[0]['seqin'].charAt(2);
	tc = tc_to_str(tc, delim);
	var i = 0;
	var err = false;
	while ( !( (tc >= edl[i]['seqin']) && (tc < edl[i]['seqout']) ) ) {
		i = i + 1;
		if (i >= edl.length) {
			err = true;
			break;
		}
	}
	
	var src_tc = '';
	var src_tape = '';
	var src_name = '';
	
	if (!err) {
		var src_delim = edl[i]['srcin'].charAt(2);
		src_tc = fc_to_str(str_to_fc(edl[i]['srcin']) + (str_to_fc(tc) - str_to_fc(edl[i]['seqin'])), src_delim);
		if ( $(qt_elem).getRate() != 0 ) {
			src_tc = src_tc.substr(0, 9) + '--';
		}
		src_tape = edl[i]['src'];
		if (src_tape == 'BL') src_tape = 'Black';
		if (src_tape == 'AX') src_tape = 'None';
		src_name = edl[i]['srcname'];
	}
	
	// display the source timecode
	if (src_tc != $(replace+'_tc').innerHTML) $(replace+'_tc').update(src_tc);
	if (src_tape != $(replace+'_tape').innerHTML) $(replace+'_tape').update(src_tape);
	if (src_name != $(replace+'_name').innerHTML) $(replace+'_name').update(src_name);
	
	return;
}

// Return string rep. of the source timecode at the given quicktime offset
var qt_to_srctc = function(offset, edl) {
	
	offset = parseInt(offset);

	// get the sequence timecode
	var seq_delim = edl[0]['seqin'].charAt(2);
	var seq_tc = tc_to_str(qt_to_tc(offset, edl[0]['seqin']), seq_delim);
	
	// find the edit in the edl
	var i = 0;
	while ( !((seq_tc >= edl[i]['seqin']) && (seq_tc < edl[i]['seqout'])) ) {
		i = i + 1;
		if (i >= edl.length) {
			//alert('offset:'+offset+' tc:'+tc+' edl.0.seqin:'+edl[0]['seqin']);
			return false;
		}
	}

	// find the source timecode based on the edit offset
	var src_delim = edl[i]['srcin'].charAt(2);
	var src_tc = fc_to_str(str_to_fc(edl[i]['srcin']) + (str_to_fc(seq_tc) - str_to_fc(edl[i]['seqin'])), src_delim);
	
	return src_tc;  // string representation 
}

/* Takes an offset (timescale 100) and returns the timecode as a string.

	If edl is defined, it will return the source timecode based on the edl.
	If there is an error returning the source timecode, the frame count will be returned.
	If edl is not defined, but start_tc is, the sequence timecode will be returned based on start_tc.
	If neither edl or start_tc are defined, the frame count will be returned.
	If frame_rate is not defined, the given offset will be returned.
*/
var tcFromOffset = function(offset) {
	if (typeof(edl) == 'object') {
		
	}
}

// Returns a 4 tuple (h, m, s, f)
// Takes at most 2 args:
//   int offset
//   str start_tc (optional, uses (global) start_tc by default)
var qt_to_tc = function() {
	
	var offset = parseInt(arguments[0]);
	var stc = (arguments[1]) ? arguments[1] : start_tc;
	var delim = stc.charAt(2);
	
	stc = str_to_tc(stc);
	
	var ofc = offset;
	sfc = tc_to_fc(stc);
	tc = fc_to_tc(sfc+ofc);

	// if non drop frame, return timecode
	if (delim == ':') { return tc; }
	
	new_min_count = tc[1];
	if (tc[0] < stc[0]) tc[0] += 24;
	if (new_min_count < stc[1]) { new_min_count += 60; tc[0] -= 1; }
	new_min_count += (tc[0]-stc[0])*60;
	dropped_frames = ((new_min_count - stc[1]) - (Math.floor(new_min_count/10) - Math.floor(stc[1]/10)))*2;
	tc = fc_to_tc(sfc+ofc+dropped_frames);
	if ((tc[3]<2) && (tc[2]==0) && (tc[1]%10!=0)) tc[3] = 2;

	// return drop frame timecode
	return tc;
}

// Return string rep. of the source timecode at the given quicktime offset
var new_qt_to_tc = function(offset) {
	var tc_tuple = qt_to_tc(offset, start_tc);
	return tc_to_str(tc_tuple, start_tc.charAt(2));
}

function get_qt_timecode(qtobj_id){
	offset = $(qtobj_id).getOffset();
	return qt_to_tc(offset);
}

var tc_to_str = function() {
	var tc = arguments[0];
	var delim = (arguments[1]) ? arguments[1] : start_tc.charAt(2);
	return zeropad(tc[0])+delim+zeropad(tc[1])+delim+zeropad(tc[2])+delim+zeropad(tc[3]);
}

/* Returns the current timecode of the quicktime player object as a string */
function str_qt_timecode(qtobj_id) {
	var offset = $(qtobj_id).getOffset();
	return Try.these(
		function() { return qt_to_srctc(offset, edl); },
		function() { return new_qt_to_tc(offset); }
	) || '';
}

function qt_to_str(offset) {
	return tc_to_str(qt_to_tc(offset));
}

var timecode_display = function(qtoffset) {
	return Try.these(
		function() { return qt_to_srctc(qtoffset, edl); },
		function() { return qt_to_str(qtoffset); }
	) || qtoffset;
}

function iskeynum(keycode) {
	// return true if they keycode is a number or keypad number
	return ([48,49,50,51,52,53,54,55,56,57,96,97,98,99,100,101,102,103,104,105].indexOf(keycode) != -1);
}
		
function tc_update_delim(tc_id) {
	var delim = ':';
	if ($F(tc_id+'_dnd') == 'drop') delim = ';';
	for (var i=1; i<=3; i+=1) $(tc_id+'_d'+i).update(delim);
}

Element.addMethods({
	isbetween: function(e_id, lowvalue, highvalue) {
		value = $F(e_id);
		for (var i=0; i<value.length; i+=1) if ('0123456789'.indexOf(value[i]) == -1) return false;
		return ((parseInt(value) >= lowvalue) && (parseInt(value) <= highvalue));
	}
});

function tc_isvalid(tc_id, hmsf) {
	// if not hmsf, check all values
	e_id = tc_id+'_'+hmsf;
	switch (hmsf) {
		case 'h': return ($(e_id).isbetween(0, 12) && ($F(e_id).length == 2));
		case 'm': return ($(e_id).isbetween(0, 59) && ($F(e_id).length == 2));
		case 's': return ($(e_id).isbetween(0, 59) && ($F(e_id).length == 2));
		case 'f':
			return ((!($(e_id).isbetween(0, 1) && ($F(tc_id+'_dnd') == 'drop') && ($F(tc_id+'_s') == '00') && (parseInt($F(tc_id+'_m')) % 10 != 0))) && ($(e_id).isbetween(0, 29) && ($F(e_id).length == 2)));
		default: return ( tc_isvalid(tc_id, 'h') && tc_isvalid(tc_id, 'm') && tc_isvalid(tc_id, 's') && tc_isvalid(tc_id, 'f') );
	}
}
function tc_massage(tc_id, hmsf) {		
	e_id = tc_id+'_'+hmsf;
	if ((hmsf == 'f') && ($F(e_id).length == 2) && $(e_id).isbetween(0, 1) && ($F(tc_id+'_dnd') == 'drop') && ($F(tc_id+'_s') == '00') && (parseInt($F(tc_id+'_m')) % 10 != 0)) $(e_id).value = '02';
}

function tc_observe(tc_id) {
	Event.observe(tc_id+'_label', 'click', function() { $(tc_id+'_h').select(); });
	['h', 'm', 's', 'f'].each( function(hmsf) {
		var e_id = tc_id+'_'+hmsf;
		Event.observe(e_id, 'click', function() { $(e_id).select(); });
		Event.observe(e_id, 'blur', function() { $(e_id).className = (tc_isvalid(tc_id, hmsf)) ? '':'error'; });
		Event.observe(e_id, 'keyup', function(e) {
			tc_massage(tc_id, hmsf);
			if ($F(e_id).length == 2) {
				$(e_id).className = (tc_isvalid(tc_id, hmsf)) ? '':'error';
			}
			if ((iskeynum(e.keyCode)) && tc_isvalid(tc_id, hmsf)) {
				if (hmsf == 'h') $(tc_id+'_m').select();
				if (hmsf == 'm') $(tc_id+'_s').select();
				if (hmsf == 's') $(tc_id+'_f').select();
			}
		});
	} );
	tc_update_delim(tc_id);
	Event.observe(tc_id+'_dnd', 'change', function() { tc_update_delim(tc_id); });
}

/* requires prototype */

var session_set = function(name, value) {
	new Ajax.Request('/a/session_set', {
		method: 'get',
		parameters: {
			'name': name,
			'value': value
		},
		onSuccess: function(transport) {
		}
	});
}

var thumb_trigger = function(trigger_id) {
	var offset = player.getOffset()/100;
	$('thumb', 'thumb_progress').invoke('toggle');
	new Ajax.Request('/a/get_thumb', {
		method: 'get',
		parameters: {
			offset: offset,
			media_id: $(trigger_id).readAttribute('media_id')
		},
		onSuccess: function(transport) { // transport.responseText
			html = '<img src="' + transport.responseText + '" />';
			$('thumb').update(html);
			$('id_thumb').value = transport.responseText;
		},
		onFailure: function(transport) {
			//alert('There was an error.');
			$$('body')[0].update(transport.responseText);
		},
		onComplete: function() {
			$('thumb', 'thumb_progress').invoke('toggle');
		}
	});
}

function xWindow(name, w, h, x, y, loc, men, res, scr, sta, too)
{
  var e='',c=',',xf='left=',yf='top='; this.n = name;
  if (document.layers) {xf='screenX='; yf='screenY=';}
  this.f = (w?'width='+w+c:e)+(h?'height='+h+c:e)+(x>=0?xf+x+c:e)+
    (y>=0?yf+y+c:e)+'location='+loc+',menubar='+men+',resizable='+res+
    ',scrollbars='+scr+',status='+sta+',toolbar='+too;
  this.opened = function() {return this.w && !this.w.closed;};
  this.close = function() {if(this.opened()) this.w.close();};
  this.focus = function() {if(this.opened()) this.w.focus();};
  this.load = function(sUrl) {
    if (this.opened()) this.w.location.href = sUrl;
    else this.w = window.open(sUrl,this.n,this.f);
    this.focus();
    return false;
  };
}

var fullscreen_media = function(id) {
	fullscreen_click('/a/fullscreen?media_id='+id);
}

var fullscreen_click = function(url) {
	var fullscreen_window = new xWindow(
		'fswin',                // target name
		screen.width,           // width
		screen.height,          // height - m is a 'fudge-factor' ;-)
		0, 0,                   // position: left, top
		0,                      // location field
		0,                      // menubar
		0,                      // resizable
		1,                      // scrollbars
		0,                      // statusbar
		0);                     // toolbar
	fullscreen_window.load(url);
	// on success
	if (fullscreen_window.opened()) {
		player.Stop();
		fullscreen_window.focus();
	}
	// on failure
	else {
		alert('Fullscreen pop-up blocked!');
	}
}
