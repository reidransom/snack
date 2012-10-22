def add_session_message(request, message):
	if not request.session.has_key('messages'):
		request.session['messages'] = []
	request.session['messages'].append(message)
