from django import template
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.conf import settings

from flow import models, tc
from flow.config import S

import re

from djblets.util.decorators import basictag

register = template.Library()

@register.tag
@basictag(takes_context=True)
def print_messages(context):
	try:
		messages = context['request'].session['messages']
	except KeyError:
		return ''
	html = '<ul>'
	for message in messages:
		html += '<li>%s</li>' % message
	html += '</ul>'
	context['request'].session['messages'] = []
	return html

@register.tag
@basictag(takes_context=True)
def media_url(context):
	if context.has_key('playlist'):
		if context['playlist']:
			if context['playlist'].id:
				return context['media'].get_url(context['playlist'].path)
	return context['media'].get_url()

@register.filter
def dict(var):
	return str(var.__dict__)

@register.filter
def as_ul(form):
	
	from django import forms
	html = ""
	
	if form.errors:
		html += '<li class="error_row">There was an error.  See below.</li>'
	
	try:
		if form.my_error:
			html += '<li class="error_row">%s</li>' % form.my_error
	except AttributeError:
		pass
	
	for field in form:
		if hasattr(field.field, 'filter_value'):
			#html += '<li class="form_row">%s%s%s</li>\n' % (field.label_tag(), str(field.field.filter_value(form.initial[field.name])), str(field.errors))
			html += '<li class="form_row">%s%s%s</li>\n' % (field.label_tag(), field.field.widget.render(field.name, field.field.filter_value(form.initial[field.name]), {'id':'id_'+field.name}), str(field.errors))
		elif isinstance(field.field.widget, forms.CheckboxInput):
			html += '<li class="form_row checkbox_row">%s%s</li>\n' % (str(field), field.label_tag())
		else:
			html += '<li class="form_row">%s%s%s</li>\n' % (field.label_tag(), str(field), str(field.errors))
	
	return mark_safe(html)

@register.filter
def prefix(string, prefix):
	if string:
		return prefix + str(string)
	return string

@register.filter
def suffix(string, suffix):
	if string:
		return str(string) + suffix
	return string

@register.filter
def pl_url(media):
	return media.pl_url(media.playlist)

@register.filter
def largest(int1, int2):
	if int1 > int2: return int1
	return int2

@register.filter
def gt(one, two):
	return one > int(two)

@register.filter
def size_selected(media, size):
	if media.displaysize == size or (media.is_custom_size() and size == 'custom'): return ' selected="selected"'
	return ''

@register.filter
def quote_duration(string):
	try:
		return string.replace(':', '\'')[:-2]
	except:
		return string

@register.filter
def replace(string, oldnew):
	(old, new) = oldnew.split(',')
	return string.replace(old, new)
sub = replace

@register.filter
def heading(string):
	return S(string).heading()

@register.filter
def marksafe(string):
	return mark_safe(string)

@register.simple_tag
def if_has_permission(user, playlist, s):
	try:
		if playlist.users.filter( id=user.id ):
			return s
	except AttributeError:
		pass
	return ''

@register.simple_tag
def if_accessible_by(playlist, user, s):
	if playlist.is_accessible_by(user):
		return s
	return ''

@register.simple_tag
def bold_phrases(text, phrases):
	def parser(match):
		return '<b>%s</b>' % match.group(0)
	words = []; quotes = []
	for phrase in phrases:
		if phrase[0] == '"':
			quotes.append(phrase[1:-1])
		words.append(phrase[:-1])
	text = re.sub(re.compile('(%s)' % '|'.join(quotes), re.I), parser, text)
	text = re.sub(re.compile('(?:[\w<]((?:%s)\w*))' % '|'.join(words), re.I), parser, text)
	return mark_safe(text)

@register.simple_tag
def from_offset(offset, media):
	return media.get_tc_calc().timecodeFromOffset(offset)

@register.filter
def tc_link(string):
	def parser(match):
		tc = match.group(0)
		if len(tc) == 8: tc = tc + match.group(1) + '00'
		return '<a class="goto_tc" timecode="%s">%s</a>' % (tc, match.group(0))
	return mark_safe(re.sub('[0-9]{2}(?P<delim>[:;])[0-9]{2}((?P=delim)[0-9]{2}){1,2}', parser, string))

@register.filter
def values(qset, value):
	return map(lambda x: x.__getattribute__(value), qset)

@register.filter
def not_in(not_list, list):
	tmp = []
	for i in list:
		if i not in not_list:
			tmp.append(i)
	return tmp

@register.simple_tag
def pipe():
	return """ <span class="pipe">&nbsp;</span>"""

@register.simple_tag
def get_attribute(request, element_id, attribute="", default=""):
	key = element_id
	if attribute: key += '_'+attribute
	return request.session.get(key, default)

@register.inclusion_tag('sidebox_media.html', takes_context=True)
def sidebox_media_id(context):
	return {'media':models.Media.objects.get(id=context['media_id'])}

@register.inclusion_tag('sidebox_media.html', takes_context=True)
def sidebox_media(context):
	return {'media':context['media']}

@register.inclusion_tag('drop_menu.html', takes_context=False)
def drop_menu(request, content_id, title=''):
	if not title: title = heading(content_id.replace('_', ' '))
	return {'request':request, 'content_id':content_id, 'title':title}

@register.simple_tag
def end_drop_menu():
	return "</div>"

@register.simple_tag
def playlist_title(playlist):
	if not playlist:
		return "Home"
	return S(playlist).heading()

@register.simple_tag
def playlist_url(playlist):
	if not playlist:
		return '/'
	return '/%s/' % playlist

@register.simple_tag
def content_width(media, is_staff, add=0):
	width = 571
	if media:
		mwidth = media.display_width()
		if mwidth > width:
			width = mwidth
	if is_staff:
		width += 220
	return width + add

@register.inclusion_tag('qt_embed.html')
def qt_embed(media, display_tc='true', autoplay='true'):
	return {
		'media':media,
		'display_tc':display_tc,
		'autoplay':autoplay,
	}

@register.inclusion_tag('qt_embed.html', takes_context=True)
def qt_embed_media(context):
	context['display_tc'] = context['media'].displaytc
	context['scale'] = 'tofit'
	context['autoplay'] = True
	return context

@register.inclusion_tag('qt_embed.html', takes_context=True)
def qt_embed_log(context):
	context['display_tc'] = True
	context['display_width'] = 320
	context['display_height'] = 240
	context['scale'] = 'aspect'
	context['autoplay'] = False
	return context

@register.inclusion_tag('tc_input.html')
def tc_input(id, value, label='', tcformat=''):
	if not label: label = S(id).replace('_', ' ').heading()
	return {'id':id, 'value':value, 'label':label, 'tcformat':tcformat}

@register.inclusion_tag('header.html', takes_context=True)
def header(context):
	return context

@register.inclusion_tag('footer.html', takes_context=True)
def footer(context):
	return context

@register.inclusion_tag('string.html', takes_context=True)
def view_url(context):
	return {'string': context['playlist'].get_url() + context['media'].name}

@register.inclusion_tag('watch_it.html', takes_context=True)
def watch_it(context):
	return context

@register.inclusion_tag('login.html', takes_context=True)
def login(context):
	return context

@register.inclusion_tag('sidebar_forms.html', takes_context=True)
def sidebar_forms(context):
	return context

@register.inclusion_tag('src_tc.html', takes_context=True)
def src_tc(context):
	return context

@register.inclusion_tag('recently_watched.html', takes_context=True)
def recently_watched(context):
	# get recent media list from the session
	rm = context['request'].session.get('recent_media', [])
	# if the current view is for a media, insert it at the top of the recent media list
	if context.has_key('media'):
		if not context['media'].playlists.filter(privacy="SEC"):
			for i in range(rm.count(context['media'].id)): rm.remove(context['media'].id) # remove duplicates
			rm.insert(0, context['media'].id)
	# remove medias that do not exist anymore
	tmp = []; medias = []
	for id in rm:
		media = None
		try:
			media = models.Media.on_site.get(id=id)
			if media.playlists.filter(privacy="SEC"):
				continue
		except models.Media.DoesNotExist:
			continue
		medias.append(media); tmp.append(id)
	# save the list of media ids back in the session
	context['request'].session['recent_media'] = tmp
	# render the recently_watched template with the updated list of medias
	return {
		'medias': medias,
	}

@register.inclusion_tag('search_box.html', takes_context=True)
def search_box(context):
	return context

@register.inclusion_tag('playlist_list.html', takes_context=True)
def playlist_list(context):
	user = context['user']
	playlist_list = models.Playlist.have_permission(user)
	return {
		'playlist_list': playlist_list,
		'user': user,
	}

@register.simple_tag
def markup(comment, media):
	return tc.parse_offsets(comment, media)

@register.inclusion_tag('player.html', takes_context=True)
def player(context):
	if context['player_settings'].has_key('poster'):
		context['player_settings']['href'] = context['player_settings']['url']
		context['player_settings']['url'] = context['player_settings']['poster']
	if not context['player_settings'].has_key('timecode'):
		context['player_settings']['timecode'] = True
	return context

@register.inclusion_tag('media_list_as_ul.html')
def media_list_as_ul(request, media_list, playlist=None):
	for media in media_list:
		if playlist:
			media.url = media.get_url(playlist.path)
		else:
			media.url = media.get_url()
	return {
		'request': request,
		'media_list': media_list,
		'playlist': playlist,
	}
