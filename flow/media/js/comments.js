var parseComment = function(comment) {
	return comment.gsub(/\b\d\d[;:]\d\d[;:]\d\d([;:]\d\d)?\b/, function(match) {
		return '[ ' + new_str_to_offset(match[0]) + ' ]';
	});
}

if ($('comment_preview')) {
	$('comment_preview').observe('click', function() {
		var params = $('post_comment_form').serialize(true);
		//params['comment'] = parseComment(params['comment']);
		new Ajax.Updater('comment_preview_element', '/a/comment_preview', {
			parameters: params
		});
	});
}

$('insert_tc').observe('click', function() {
	$('id_comment').insertAtCursor('[ ' + player.getOffset() + ' ]');
});

$('post_comment').observe('click', function() {
	var params = $('post_comment_form').serialize(true);
	//params['comment'] = parseComment(params['comment']);
	new Ajax.Updater('comment_preview_element', '/a/post_comment', {
		parameters: params,
		onSuccess: function() {
			$('comment_preview_element').update('');
			$('id_person_name').value = '';
			$('id_comment').value = '';
		},
		onComplete: function() {
		},
		insertion: 'after'
	});
});

var delete_comment = function(comment_id) {
	new Ajax.Request('/a/delete_comment', {
		method: 'get',
		parameters: {
			'comment_id': comment_id
		},
		onSuccess: function() {
			$('comment_'+comment_id).remove();
		},
		onComplete: function() {
		}
	});
}

$('show_comment_form').observe('click', function() {
	$('post_comment_form').setStyle({display:'block'});
	$('show_comment_form').hide();
});
