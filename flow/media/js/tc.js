// Helper
var isDrop = function(tc) {
	return (tc.charAt(2) == ";");
}

// Helper
var tcToTuple = function(tc) {
	var d = tc.charAt(2);
	var tc_tuple = tc.split(d);
	return [ parseInt(tc_tuple[0]), parseInt(tc_tuple[1]), parseInt(tc_tuple[2]), parseInt(tc_tuple[3]) ];
}

// Helper
var tupleToTc = function(tc_tuple, d) {
	return tc_tuple[0].toPaddedString(2) + d + tc_tuple[1].toPaddedString(2) + d + tc_tuple[2].toPaddedString(2) + d + tc_tuple[3].toPaddedString(2);
}

var TimecodeCalc = Class.create({
	// Constructor
	initialize: function() {
		this.start_tc = false;
		this.edl = false;
		if (typeof(arguments[0]) == 'string') {
			this.start_tc = arguments[0];
		}
		else {
			this.edl = arguments[0];
		}
		this.fps = (arguments[1]) ? arguments[1] : 30;
		this.edit_index = 0;
	},
	// Helper
	tcToFc: function(tc) {
		var d = tc.charAt(2);
		tc = tc.split(d);
		return parseInt(tc[0])*this.fps*3600 + parseInt(tc[1])*this.fps*60 + parseInt(tc[2])*this.fps + parseInt(tc[3]);
	},
	// Helper
	fcToTc: function(fc) {
		var fc = arguments[0];
		var d = (arguments[1]) ? arguments[1] : ":";
		var tc = [ Math.floor((fc/(this.fps*3600.0))%24), Math.floor(fc%(this.fps*3600.0)/(this.fps*60.0)), Math.floor(fc%(this.fps*60.0)/this.fps), fc%this.fps ];
		return tupleToTc(tc, d);
	},
	// Helper
	offsetToFc: function(offset) {
		return Math.floor((offset*this.fps)/100);
	},
	
	timecodePlusFc: function(start_tc, offset_fc) {
		var d = start_tc.charAt(2);
		var start_fc = this.tcToFc(start_tc);
		var fc = start_fc + offset_fc;
		var tc = this.fcToTc(fc, d);
		
		// If the timecode format is not drop frame, return timecode
		if ( ! ((d == ";") && (this.fps == 30)) ) {
			return tc;
		}
	
		// If it is drop frame, calculate and return the adjusted timecode
		var start_tc_tuple = tcToTuple(start_tc);
		var tc_tuple = tcToTuple(tc);
		if (tc_tuple[0] < start_tc_tuple[0]) {
			tc_tuple[0] = tc_tuple[0] + 24;
		}
		var minutes_elapsed = ((tc_tuple[0]*60) + tc_tuple[1]) - ((start_tc_tuple[0]*60) + start_tc_tuple[1]);
		var dropped_frames = ( minutes_elapsed - (Math.floor(tc_tuple[1]/10) - Math.floor(start_tc_tuple[1]/10)) ) * 2;
		tc = this.fcToTc(fc + dropped_frames, d);
		tc_tuple = tcToTuple(tc);
		if ( (tc_tuple[3] < 2) && (tc_tuple[2] == 0) && (tc_tuple[1]%10 != 0) ) {
			tc_tuple[3] = 2;
			tc = tupleToTc(tc_tuple, d);
		}
		return tc;
	},
	
	editFromOffset: function(offset) {
		var seq_tc = this.timecodePlusFc(this.edl[0]['seqin'], this.offsetToFc(offset));
		var i = 0;
		while (!((seq_tc >= this.edl[this.edit_index]['seqin']) && (seq_tc < this.edl[this.edit_index]['seqout']))) {
			this.edit_index = this.edit_index + 1;
			if (this.edit_index >= this.edl.length) {
				this.edit_index = 0;
			}
			i = i + 1;
			if (i >= this.edl.length) {
				return false;
			}
		}
		return this.edl[this.edit_index];
	},
	
	// Given an offset, returns string representation of a timecode
	timecodeFromOffset: function(offset) {
		if (this.edl) {
			var edit = this.editFromOffset(offset);
			if (!edit) {
				// Return the offset frame count
				return this.offsetToFc(offset)+'';
			}
			var offset_fc = this.offsetToFc(offset) + this.tcToFc(this.edl[0]['seqin']) - this.tcToFc(edit['seqin']);
			return this.timecodePlusFc(edit['srcin'], offset_fc);
		}
		return this.timecodePlusFc(this.start_tc, this.offsetToFc(offset));
	},

	srcNameFromOffset: function(offset) {
		var edit = this.editFromOffset(offset);
		if (!edit) {
			return '';
		}
		return edit['src']
	}

});
