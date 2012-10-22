var Log = Class.create({
	
	// Constructor
	initialize: function(log, media_id, tc_calc, player) {
		
		this.log = log;
		this.log_elem = $('log');
		this.media_id = media_id;
		this.tc_calc = tc_calc;
		this.player = player;
		
		new HotKey('j', function(event) {
			this.rewind();
		});
		new HotKey('k', function(event) {
			this.play_pause();
		});
		new HotKey('l', function(event) {
			this.forward();
		});
		this.player.observe('click', this.set_play_pause_button.bind(this));
		
		new PeriodicalExecuter(this.save.bind(this), 60);
		Event.observe(window, 'unload', this.save.bind(this));

		var i = 0;
		for (i=0; i<this.log.length; ++i) {
			this.clip_insert(i);
		}

		if (!this.log) {
			this.add_clip();
		}

	},

	rewind: function() {
		this.player.rewind();
	},

	play_pause: function() {
		this.player.playpause();
		this.set_play_pause_button();
	},

	set_play_pause_button: function() {
		if (!$('play_pause')) {
			return;
		}
		if ((this.player.getRate() == 0) && ($('play_pause').hasClassName('pause'))) {
			$('play_pause').removeClassName('pause');
			$('play_pause').addClassName('play');
		}
		if ((this.player.getRate() != 0) && ($('play_pause').hasClassName('play'))) {
			$('play_pause').removeClassName('play');
			$('play_pause').addClassName('pause');
		}
	},

	forward: function() {
		this.player.forward();
	},

	clip_insert: function() {
		
		var row_id = arguments[0];
		var insert = (arguments[1]) ? arguments[1] : false;
		
		var clip = this.log[row_id];
		var clip_html = new Template(
			'<div id="row_#{row_id}" class="row">' +
				'<a class="tc">#{timecode}</a>' +
				'<a class="delete"></a>' +
				'<div class="text" row_id="#{row_id}">' +
					'#{text}' +
				'</div>' +
			'</div>'
		).evaluate({
			'row_id': row_id,
			'timecode': this.tc_calc.timecodeFromOffset(clip.start),
			'text': clip.text.gsub('\n', '<br />')
		});
		
		this.log_insert(clip_html, insert, row_id);

		var row = $('row_'+row_id);
		var thisObj = {
			log: this,
			row_id: row_id,
			row: row
		}
		row.select('a.delete')[0].observe('click', function() {
			this.delete_clip(row_id);
		}.bind(this, row_id));
		row.select('div.text')[0].observe('click', function() {
			this.clip_form_insert(row_id, ['replace', row]);
		}.bind(this, row_id, row));
		row.select('a.tc')[0].observe('click', function() {
			this.player.setOffset(this.log[row_id].start);
		}.bind(this, row_id));
	},

	log_insert: function(html, insert, row_id) {
		
		if (typeof(insert) == 'object') {
			if (insert[0] == 'replace') {
				insert[1].replace(html);
			}
			else {
				insert_dict = {}
				insert_dict[insert[0]] = html;
				insert[1].insert(insert_dict);
			}
		}
		else if (typeof(row_id) == 'number') {
			var offset = this.log[row_id].start;
			var smallest_diff = offset - this.log[0].start;
			var i = 0;
			var index = 0;
			$A(this.log).each(function(clip) {
				if (!clip) return;
				var diff = offset - clip.start;
				if ((diff > 0) && (diff < smallest_diff)) {
					smallest_diff = diff;
					index = i;
				}
				i += 1;
			});
			if (index > 0) {
				$('row_'+index).insert({'after': html});
			}
			else {
				this.log_elem.insert({'bottom': html});
			}
		}
	},
		
	clip_form_insert: function() {
		
		var row_id = arguments[0];
		var insert = (arguments[1]) ? arguments[1] : false;
		
		this.log_elem.select('div.form_row').each(function(row) {
			var row_id = row.identify().substring(4)*1;
			this.log[row_id].text = $F(row.select('textarea')[0]);
			this.save_clip(row_id);
			this.clip_insert(row_id, ['replace', row]);
		}.bind(this));
		
		var clip = this.log[row_id];
		var clip_form_html = new Template(
			'<div id="row_#{row_id}" class="form_row">' +
				'<a class="tc">#{timecode}</a>' +
				'<div class="text">' +
					'<textarea class="autogrow">#{text}</textarea>' +
					'<div class="tacp">' +
						'<a class="add_clip" title="Add Clip [Enter]"></a>' +
						'<a class="mark_in" title="Mark In [Ctl+I]"></a>' +
						'<a class="rewind" title="Rewind [Ctl+J]"></a>' +
						'<a id="play_pause" class="play" title="Play/Pause [Ctl+K]"></a>' +
						'<a class="forward" title="Fast Forward [Ctl+L]"></a>' +
					'</div>' +
				'</div>' +
			'</div>'
		).evaluate({
			'row_id': row_id,
			'timecode': this.tc_calc.timecodeFromOffset(clip.start),
			'text': clip.text
		});

		this.log_insert(clip_form_html, insert, row_id);
		
		var row = $('row_'+row_id);
		row.select('a.tc')[0].observe('click', function() {
			this.player.setOffset(this.log[row_id].start);
		}.bind(this));
		row.select('div.tacp a.add_clip')[0].observe('click', this.add_clip.bind(this));
		row.select('div.tacp a.mark_in')[0].observe('click', this.mark_in.bind(this));
		row.select('div.tacp a.rewind')[0].observe('click', this.rewind.bind(this));
		$('play_pause').observe('click', this.play_pause.bind(this));
		row.select('div.tacp a.forward')[0].observe('click', this.forward.bind(this));
		this.set_play_pause_button();
	},

	mark_in: function() {
		var row = this.log_elem.select('div.form_row')[0];
		var row_id = row.identify().substring(4)*1;
		this.log[row_id].start = this.player.getOffset();
		this.log[row_id].text = $F(row.select('textarea')[0]);
		row.remove();
		this.clip_form_insert(row_id);
	},

	add_clip: function() {
		var row_id = this.log.push({
			start: this.player.getOffset(),
			text: '',
			id: false
		}) - 1;
		this.clip_form_insert(row_id);
	},

	save: function() {
		this.log_elem.select('div.form_row').each(function(row) {
			var row_id = row.identify().substring(4)*1;
			this.log[row_id].text = $F(row.select('textarea')[0]);
			this.save_clip(row_id);
		}.bind(this));
	},
	
	save_clip: function(row_id) {
		var clip = this.log[row_id];
		if ((!clip.text) && (clip.id)) {
			new Ajax.Request('/a/delete_clip', {
				method: 'post',
				parameters: {
					'clip_id': clip.id
				}
			});
			this.log[row_id] = false;
		}
		if (clip.text) {
			new Ajax.Request('/a/save_clip', {
				method: 'post',
				parameters: {
					media_id: this.media_id,
					clip_id: clip.id,
					start: clip.start,
					text: clip.text
				},
				onSuccess: function(transport) {
					if (!clip.id) {
						this.log[row_id].id = transport.responseText;
					}
				},
				onFailure: function(transport) {
					//alert('There was an error.');
					$$('body')[0].update(transport.responseText);
				}
			});
		}
	}

});
