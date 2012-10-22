# todo: remove unnecessary imports
from django import forms
from django.contrib import auth
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib.comments.views.comments import post_comment
from django.contrib.comments.models import Comment
from django.contrib.comments.views import moderation
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.serializers import serialize, deserialize
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template.loader import render_to_string
from django.template import Context, Template, RequestContext
from django.utils.html import escape
from django.utils.http import urlquote
from django.utils.safestring import mark_safe

from django.conf import settings
from flow import models
from multisite.models import current_site, users_on_site

import os, datetime, re
#import Stemmer
import urllib, minjson, tc

ALL_VIDEOS_PLAYLIST = {
'name':  '',
	'path': 'all',
	'published': False,
	'get_url': '/all/',
	'no_settings': True,
	'medias': [],
}

STOPWORDS = [
	"i", 
	"a",
	"about",
	"an",
	"are",
	"as",
	"at",
	"be",
	"by",
	"com",
	"de",
	"en",
	"for",
	"from",
	"how",
	"in",
	"is",
	"it",
	"la",
	"of",
	"on",
	"or",
	"that",
	"the",
	"this",
	"to",
	"was",
	"what",
	"when",
	"where",
	"who",
	"will",
	"with",
	"und",
	"the",
	"www",
]

def form_get_tc(form_data, id):
	return form_data[id+'_tc']
	
def form_get_bool(form_data, id):
	if form_data.has_key(id): return True
	return False

def form_get_size(form_data, id):
	t = form_data[id+'_size'];
	if t == 'custom': return '%sx%s' % (form_data[id+'_width'], form_data[id+'_height'])
	return t

def feed(request, playlist=None):
	playlist = get_object_or_404(models.Playlist, path=playlist)
	playlist.sync()
	r = render_to_response(
		'feed.html',
		{
			'playlist': playlist,
			'medias': playlist.media_set.all().order_by('-pub_date'),
		},
		context_instance = RequestContext(request),
	)
	r['Content-Type'] = 'text/xml; charset-utf-8'
	return r

def delete_playlist(request):
	id = request.GET['id']
	models.Playlist.on_site.get(id=id).delete()
	return HttpResponseRedirect('/')

def delete_clip(request):
	clip_id = request.POST['clip_id']
	models.Clip.on_site.get(id=clip_id).delete()
	return HttpResponse('')

def save_clip(request):
	clip_id = request.POST.get('clip_id', '')
	if clip_id:
		clip = models.Clip.on_site.get(id=clip_id)
	else:
		clip = models.Clip(media=models.Media.on_site.get(id=request.POST['media_id']))
	clip.start = request.POST['start']
	clip.text = request.POST['text']
	clip.save()
	return HttpResponse(str(clip.id))

def logout(request):
	recent_media = request.session.get('recent_media', [])
	auth.logout(request)
	request.session['recent_media'] = recent_media
	return HttpResponseRedirect('/signin')

def get_thumb(request):
	if not request.user.is_staff: return HttpResponseForbidden('<h1>Forbidden</h1>')
	
	media = models.Media.objects.get(id=request.GET['media_id'])
	offset = request.GET['offset']

	#thumbfn = models.Media.path('thumb', models.Media.randStr(media.playlist, media.name)+'.jpg')
	thumbfn = media.tempBasename('thumb', '.jpg')
	fn = thumbfn.replace('thumb', 'thumb32', 1)
	models.Media.ffmpegImageGrab(media.get_file_path(), os.path.join(settings.UPLOAD_ROOT, fn), (32,24), offset)
	fn = thumbfn.replace('thumb', 'thumb64', 1)
	models.Media.ffmpegImageGrab(media.get_file_path(), os.path.join(settings.UPLOAD_ROOT, fn), (64,48), offset)
	
	return HttpResponse(settings.UPLOAD_URL + fn)

def download_encode(request):
	if not request.user.is_staff: return HttpResponseForbidden('<h1>Forbidden</h1>')
	media_id = request.GET['media_id']
	media = models.Media.objects.get(id=media_id)
	cmd = media.download_encode()
	return HttpResponse(cmd)

# If user requested login, try to log them in
def login(request):
	user = auth.authenticate(username=request.POST['username'], password=request.POST['password'])
	if user is not None:
		if user.is_active:
			auth.login(request, user)
		else:
			# disabled user account
			pass
	else:
		# invalid login
		return HttpResponseRedirect(request.POST.get('redirect', '/') + '?error=login')
		pass
	return HttpResponseRedirect(request.POST.get('redirect', '/'))

def watch_it(request):
	return HttpResponseRedirect('/%s' % request.POST['media'])
	
def delete_comment(request):
	if not request.user.is_staff: return HttpResponseForbidden('<h1>Forbidden</h1>')
	comment_id = request.GET['comment_id']
	moderation.delete(request, comment_id)
	#try:
	#	comment = Comment.objects.get(id=comment_id)
	#except Comment.DoesNotExist:
	#	return HttpResponseNotFound("<h1>Comment not found</h1>")
	#comment.delete()
	#return HttpResponse(comment_id)
	return HttpResponseRedirect(request.GET['redirect'])

def session_set(request):
	request.session[request.GET['name']] = request.GET['value']
	return HttpResponse(request.GET['name']+'='+request.session[request.GET['name']])

def remove_edl(request):
	if not request.user.is_staff: return HttpResponseForbidden('<h1>Forbidden</h1>')
	media = models.Media.objects.get(id=request.GET['media_id'])
	media.edl = ''
	media.timecode_display = settings.TC_TRACKS[0][0]
	media.save()
	return HttpResponse('edl removed')

def media_fullscreen(request, media):
	player_settings = {
		'url': media.get_file_url(),
		'width': '100%',
		#'height': media.get_display_height(320),
		#'height': '100%',
		'controller': 'true',
		'bgcolor': '#000000',
		'autoplay': 'false',
		'scale': 'aspect',
		'timecode': media.displaytc,
	}
	return render_to_response(
		'fullscreen.html',
		{
			'media': media,
			'player_settings': player_settings,
		},
		context_instance = RequestContext(request),
	)
	
def comment_preview(request):
	media_id = request.POST['target'].split(':')[1]
	media = models.Media.objects.get(id=media_id)
	comment = {
		'person_name': request.POST['person_name'],
		'comment': tc.parse_offsets(request.POST['comment'], media),
		'delete_able': False,
		'submit_date': datetime.datetime.now(),
		'is_preview': True,
		'media': media,
	}
	return render_to_response(
		'comment.html',
		{
			'comment': comment,
		},
		context_instance = RequestContext(request),
	)

#def post_comment(request):
	#post_comment(request)
	#target, person_name = request.POST['target'], request.POST['person_name']
	#content_type_id, object_id = target.split(':')
	#comment = Comment.objects.filter(person_name=person_name, content_type=content_type_id, object_id=object_id).order_by('-submit_date')[0]
	#if request.user.is_staff: comment.delete_able = True
	#media = models.Media.objects.get(id=object_id)
	#comment.comment = tc.parse_offsets(comment.comment, media)
	#return render_to_response('comment.html', {
	#	'comment':comment,
	#	'media': media,
	#})

def save_playlist(request):
	if not request.user.is_staff: return HttpResponseForbidden('<h1>Forbidden</h1>')

	playlist = models.Playlist.objects.get(id=request.POST['playlist_id'])
	playlist.published = form_get_bool(request.POST, 'published')
	playlist.save()

def search(request, query):
	results = []
	tapes = []
	stopped = []
	phrases = []
	#stem = Stemmer.Stemmer('english')
	stems = []
	if query and request.user.is_staff:
		phrases = re.compile('((?:\w+)|(?:".+"))').findall(query)
		for i in range(len(phrases)):
			if phrases[i] in STOPWORDS:
				stopped.append(phrases[i])
				phrases[i] = ''
				continue
			if re.compile('\w+').match(phrases[i]):
				#stems.append(stem.stemWord(phrases[i]) + "*")
				pass
		for i in range(phrases.count('')): phrases.remove('')
		phrases.extend(stems)
		fts_query = " OR ".join(phrases)
		for result in models.search(fts_query, request.user):
			media = models.Media.objects.get(id=result[0])
			clip = models.Clip.objects.get(id=result[1])
			def qparser(match):
				return '<b>%s</b>' % match.group(0)
			def wparser(match):
				return match.group(0)[0] + '<b>%s</b>' % match.group(1)
			words = []; quotes = []
			for phrase in phrases:
				if phrase[0] == '"':
					quotes.append(phrase[1:-1])
				words.append(phrase[:-1])
			clip.bolded_text = escape(clip.get_text())
			if quotes: clip.bolded_text = re.sub(re.compile('(%s)' % '|'.join(quotes), re.I), qparser, clip.get_text())
			if words: clip.bolded_text = re.sub(re.compile('\W((?:%s)\w*)' % '|'.join(words), re.I), wparser, " "+clip.bolded_text)
			results.append( {'media':media, 'clip':clip} )
	
	if query:
		medias = models.Media.objects.filter( Q(name__icontains=query)|Q(title__icontains=query)|Q(description__icontains=query) )
		medias = medias.exclude(name='__default__')
		medias = medias.filter(playlists__in=request.user.playlists)
		for media in medias: media.url = media.db_url()
	
	return render_to_response(
		'search.html',
		{
			'medias':medias,
			'results':results,
			'stopped':stopped,
			'phrases':phrases,
			'request':request,
		},
		context_instance = RequestContext(request),
	)

def save_media(request):
	
	if not request.user.is_staff: return HttpResponseForbidden('<h1>Forbidden</h1>')
	
	media = models.Media.objects.get(id=request.POST['media_id'])
	media.title = request.POST['title']
	media.description = request.POST['description']
	media.starttc = form_get_tc(request.POST, 'start')
	media.displaytc = form_get_bool(request.POST, 'display_tc')
	media.displaysize = form_get_size(request.POST, 'display')
	media.display_comments = form_get_bool(request.POST, 'display_comments')
	media.thumb = request.POST['thumb_file'].replace('thumb64', 'thumb', 1)
	
	if request.FILES.has_key('edl_file'):
		media.importEDL(request.FILES['edl_file']['content'], request.FILES['edl_file']['filename'])
	
	media.save()
	
	# to do: thumb clean up, maybe use cron jobs to clean up

def action(request, action):
	return eval(action)(request)

def site_settings(request):
	if not request.user.is_staff: return HttpResponseForbidden('<h1>Forbidden</h1>')
	media = models.Media.objects.get(name='__default__', playlist='__default__')
	apply_to = request.GET.get('apply_to', '')
	if apply_to:
		if apply_to == 'start_tc':
			alter_column(models.Media, 'starttc', form_get_tc(request.GET, 'start'))
		if apply_to == 'display_tc':
			alter_column(models.Media, 'displaytc', form_get_bool(request.GET, 'display_tc'))
		if apply_to == 'display_size':
			alter_column(models.Media, 'displaysize', form_get_size(request.GET, 'display'))
		if apply_to == 'display_comments':
			alter_column(models.Media, 'display_comments', form_get_bool(request.GET, 'display_comments'))
		for m in models.Media.objects.filter(id=request.GET.get('apply_to', '')):
			m.starttc = form_get_tc(request.GET, 'start_tc')
			m.displaytc = form_get_bool(request.GET, 'display_tc')
			m.displaysize = form_get_size(request.GET, 'display')
			m.display_comments = form_get_bool(request.GET, 'display_comments')
			m.save()
		return HttpResponse('success')
	tmpl = 'site_settings.html'
	return render_to_response(
		tmpl,
		{
			'media':media,
			'request':request,
		},
		context_instance = RequestContext(request),
	)

def print_log(request, media):
	
	if not request.user.is_staff: return HttpResponseForbidden('<h1>Forbidden</h1>')
	
	return render_to_response(
		'print_log.html',
		{
			'request': request,
			'media': media,
			'clip_list': media.clip_set.all().order_by('start'),
		},
		context_instance = RequestContext(request),
	)

@user_passes_test(lambda u: current_site.info.is_staff(u))
def media_edit(request, media):
	
	class MediaForm(forms.ModelForm):
		description = forms.CharField(
			required=False,
			widget=forms.Textarea(attrs={'rows':'2'})
		)
		timecode_display = forms.ChoiceField(choices=media.tc_tracks(), required=False)
		class Meta:
			model = models.Media
			fields = ('title', 'description', 'timecode_display', 'displaytc', 'display_comments', 'playlists', 'starttc', 'display_size', 'display_width', 'display_height', 'frame_rate', 'pub_date')
	
	media_form = MediaForm(instance=media)
	
	if request.POST.get('save', '') == 'Save':
		media_form = MediaForm(request.POST, instance=media)
		try:
			media_form.save()
			media.thumb = request.POST['thumb_file'].replace('thumb64', 'thumb', 1)
			if request.FILES.has_key('edl_file'):
				media.importEDL(request.FILES['edl_file'].read(), request.FILES['edl_file'].name)
			media.save()
		except ValueError:
			pass
	
	html = '<label for="id_playlists">Playlists</label><div class="input"><select id="id_playlists" name="playlists" multiple="multiple">'
	for pl in models.Playlist.on_site.all().exclude(path="__default__"):
		selected = ''
		if pl in media.playlists.all():
			selected = ' selected="selected"'
		html += '<option value="%s"%s>%s</option>' % (pl.id, selected, pl.name)
	html += '</select></div>'
	media_form.playlists_html = mark_safe(html)
	
	return render_to_response(
		'media_edit.html',
		{
			'request': request,
			'media': media,
			'media_form': media_form,
			'player_settings': media.get_player_settings(),
			'view': 'edit',
		},
		context_instance = RequestContext(request),
	)


@user_passes_test(lambda u: current_site.info.is_staff(u))
def media_log(request, media):
	
	class LogHeaderForm(forms.Form):
		title = forms.CharField(required=False)
		description = forms.CharField(
			required=False,
			widget=forms.Textarea(attrs={'rows':'2'})
		)
		logger = forms.CharField(required=False)
		date_shot = forms.DateField(required=False)
		date_logged = forms.DateField(required=False)
		tape_format = forms.ChoiceField(choices=settings.TAPE_FORMAT_CHOICES, required=False)
		timecode_display = forms.ChoiceField(choices=media.tc_tracks())

	log_header_form = LogHeaderForm()
	if request.POST.get('log_header', '') == 'Save Log Details':
		log_header_form = LogHeaderForm(request.POST)
		if log_header_form.is_valid():
			media.__dict__.update(log_header_form.cleaned_data)
			media.save()
	
	if not log_header_form.is_bound or log_header_form.is_valid():
		log_header_form = LogHeaderForm(media.__dict__)
			
	player_settings = {
		'url': media.get_file_url(),
		'width': 320,
		'height': media.get_display_height(320),
		'autoplay': 'false',
	}

	context = {
		'request': request,
		'media': media,
		'clip_list': media.clip_set.all().order_by('start'),
		'log_header_form': log_header_form,
		'player_settings': player_settings,
		'view': 'log',
	}
	return render_to_response('log.html', context, context_instance=RequestContext(request))

def media(request, media='', id='', playlist=None, view=''):
	
	request.user.playlists = models.Playlist.have_permission(request.user)
	
	if request.POST.get('submit', '') == 'Post Comment':
		post_comment(request)
	if request.POST.get('submit', '') == 'delete_comment':
		comment_id = request.POST.get('comment_id')
		moderation.delete(request, comment_id)
	
	name = media
	media = None
	
	media = get_object_or_404(models.Media, id=id, site=current_site)
	
	if playlist:
		playlist = get_object_or_404(models.Playlist, path=playlist, site=current_site)
	
	if name != media.name:
		raise Http404
	if not playlist and media.playlists.filter(privacy="SEC"):
		raise Http404
	if playlist:
		if playlist.privacy == "SEC" and not playlist.is_accessible_by(request.user):
			raise Http404
		if not playlist in media.playlists.all():
			raise Http404
	
	# Make sure the video file hasn't been deleted from the filesystem
	# If it has, media.sync() will remove it from the database and get_object_or_404(...)
	# will return 404 error
	media.sync()
	get_object_or_404(models.Media, id=id)
	
	# This is for returning log view, print_log view, etc.
	if view:
		return eval('media_'+view)(request, media)
	
	context = {
		'media': media,
		'playlist': playlist,
		'player_settings': media.get_player_settings(),
		'view': 'view',
	}
	return render_to_response('media.html', context, context_instance=RequestContext(request))

@user_passes_test(lambda u: current_site.info.is_authenticated(u), login_url='/signin')
def index(request):
	return HttpResponseRedirect('/playlist/all')

class AlphaNumericField(forms.CharField):
	def clean(self, value):
		if not value:
			raise forms.ValidationError('Required')
		if not re.compile('^[\w_]+$').match(value):
			raise forms.ValidationError('Only letters, numbers, and underscores are allowed.')
		return value

class PlaylistForm(forms.ModelForm):
	description = forms.CharField(
		required=False,
		widget=forms.Textarea(attrs={'rows':'2'})
	)
	path = AlphaNumericField(label="Short Name", required=True)
	
	class Meta:
		model = models.Playlist
		#fields = ('name', 'path', 'description', 'privacy', 'published', 'users', 'site_id')
		fields = ('name', 'path', 'description', 'privacy', 'published', 'site_id')

def add_playlist(request):
	
	if not request.user.is_staff: return HttpResponseForbidden('<h1>Forbidden</h1>')
	
	playlist_form = PlaylistForm()
	
	if request.POST.get('save', '') == 'Save':
		
		playlist = models.Playlist(site_id=current_site.id)
		playlist_form = PlaylistForm(request.POST, instance=playlist)
		
		if playlist_form.is_valid():
			playlist_form.my_error = ''
			
			if models.Playlist.on_site.filter(path=playlist_form.cleaned_data['path']):
				playlist_form.my_error = "A playlist already exists with that short name."
		
			if not playlist_form.my_error:
				try:
					playlist = playlist_form.save()
					return HttpResponseRedirect(reverse('flow.views.playlist', args=[playlist.path, 'edit']))
				except ValueError:
					pass
	
	return render_to_response(
		'playlist_edit.html',
		{
			'playlist_form': playlist_form,
			'playlist': None,
			'request': request,
			'view': 'edit',
		},
		context_instance = RequestContext(request),
	);

@user_passes_test(lambda u: current_site.info.is_staff(u), login_url='/signin')
def playlist_edit(request, playlist):
	
	playlist_form = PlaylistForm(instance=playlist)

	if request.POST.get('save', '') == 'Save':
		playlist_form = PlaylistForm(request.POST, instance=playlist)
		try:
			playlist_form.save()
		except ValueError:
			pass
	
	return render_to_response(
		'playlist_edit.html',
		{
			'playlist_form': playlist_form,
			'playlist': playlist,
			'view': 'edit',
		},
		context_instance = RequestContext(request),
	);

def playlist_redirect(request, playlist, media=None):
	playlist = get_object_or_404(models.Playlist, site=current_site, path=playlist)
	if media:
		media = get_object_or_404(models.Media, site=current_site, name=media, playlists=playlist)
		return HttpResponseRedirect(reverse('flow_playlist_media', args=[playlist.path, media.id, media.name]))
	return HttpResponseRedirect(reverse('flow.views.playlist', args=[playlist.path]))

def playlist(request, playlist, view=''):
	
	request.user.playlists = models.Playlist.have_permission(request.user)

	smart_pl_paths = map(lambda pl: pl.path, models.SMART_PLAYLISTS)
	if playlist in smart_pl_paths:
		playlist = models.SMART_PLAYLISTS[smart_pl_paths.index(playlist)]
		playlist.no_settings = True
		playlist.medias = []
		
		# define media list for all smart playlists here
		if playlist.path == 'all':
			playlists = models.Playlist.have_permission(request.user, True)
			for p in playlists:
				if p.path != 'all':
					p.sync()
			if request.user.is_staff:
				playlist.medias = models.Media.on_site.all().exclude(name='__default__')
			else:
				playlist.medias = models.Media.on_site.filter(
					playlists__in = playlists,
				).distinct()
			playlist.medias = playlist.medias.order_by('-pub_date')
			#playlist.medias = models.Media.on_site.filter(
			#	playlists__in = playlists,
			#).distinct().order_by('-pub_date')
	
	else:
		playlist = get_object_or_404(models.Playlist, path=playlist, site=current_site)
		
		if not playlist.is_accessible_by(request.user):
			# Secure playlists get "cloaked" (404 Not Found)
			if playlist.privacy == 'SEC':
				raise Http404
			# Authenticated users without access to this playlist get denied (403 Fobidden)
			if request.user.is_authenticated():
				return HttpResponseForbidden('<h1>Forbidden</h1>')
			# Unauthenticated user + playlist that's not "cloaked" = redirect to login page (on successful login, redirect to this playlist)
			return HttpResponseRedirect( reverse('flow_login_required') + '?next=' + urlquote(request.get_full_path()) )

		if view:
			return eval('playlist_'+view)(request, playlist)
		
		playlist.sync()
		playlist.medias = playlist.media_set.all().order_by('-pub_date')

	return render_to_response(
		'playlist.html',
		{
			'playlist':playlist,
			'view': 'view',
		},
		context_instance = RequestContext(request),
	);
