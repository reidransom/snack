from django.db import models, connection
from django.db.models import Q
from django.contrib.auth.models import User
from django.http import Http404
#from django.contrib.comments.models import FreeComment
from django.contrib import admin
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

from django.conf import settings

from flow import ffinfo
from flow.config import *

from multisite.models import current_site

import os
import time
from datetime import datetime
from urlparse import urlparse
import popen2, tempfile

import minjson, tc

class Playlist(models.Model):
	name = models.CharField(max_length=256)
	path = models.CharField(max_length=256, blank=True)
	description = models.TextField(blank=True)
	published = models.BooleanField()
	privacy = models.CharField(
		max_length=5,
		choices=[
			('PUB', 'Published'),
			('PAS', 'Passive'),
			#('SEC', 'Secure'),
		],
		default='PAS',
	)
	digest = models.CharField(max_length=32, blank=True)
	users = models.ManyToManyField(User)
	site = models.ForeignKey(Site)

	objects = models.Manager()
	on_site = CurrentSiteManager()
	
	def __str__(self):
		return str(self.name)
	
	def get_url(self):
		return reverse('flow.views.playlist', args=[self.path])
	
	def sync(playlist):
		"""Sync a folder of videos.
		"""
		
		#return # disable syncing for debugging
      
		# sync each media entry related to this playlist
		medias = playlist.media_set.all()
		for media in medias:
			media.sync()
		
		plpath = playlist.path
		if playlist.path == 'home':
			plpath = ''
		plpath = os.path.join(settings.UPLOAD_ROOT, plpath, '')
		if not os.path.isdir(plpath):
			return # folder does not exist
		
		fs_digest = get_digest(plpath)
		if playlist.digest == fs_digest:
			return # folder has not changed
		
		# sync each video in the playlist folder
		filenames = map(lambda x: os.path.join(plpath, x), os.listdir(plpath))
		for filename in filenames:
			if not os.path.splitext(filename)[1] in settings.VIDEO_EXTENSIONS:
				continue
			sync_file(filename)
		
		playlist.digest = fs_digest
		playlist.save()
		return # sunk

	def is_accessible_by(self, user):
		"""Returns True if the user has permission to this playlist, False otherwise."""
		return user.is_staff or self.privacy == "PUB" or self.users.filter( id=user.id )
	
	@staticmethod
	def have_permission(user, exclude_secure=False):
		'''Returns a list of Playlists that user has permission to.'''
		playlist_list = []
		if current_site.info.is_authenticated(user):
			if user.is_staff:
				playlist_list = Playlist.on_site.all()
			else:
				playlist_list = Playlist.on_site.filter( Q(users=user) | Q(privacy="PUB") ).distinct()
			if exclude_secure:
				playlist_list = playlist_list.exclude( privacy="SEC" )
		else:
			playlist_list = Playlist.on_site.filter( privacy="PUB" )
		return SMART_PLAYLISTS + list(playlist_list)
	
#admin.site.register(Playlist)

SMART_PLAYLISTS = [
	Playlist(
		name = 'All Videos',
		path = 'all',
		published = False,
	)
]

class Media(models.Model):
	
	name = models.CharField(max_length=256)
	playlists = models.ManyToManyField(Playlist, blank=True)
	#file = models.FileField(upload_to='/')
	file = models.FileField(upload_to='/uploads/')
	#download = models.FileField(upload_to='/', blank=True)
	download = models.FileField(upload_to='/uploads/', blank=True)
	title = models.CharField(max_length=256)
	description = models.TextField(blank=True)
	pub_date = models.DateTimeField('date published')
	duration = models.CharField(max_length=11, null=True, blank=True)
	starttc = models.CharField(max_length=11, null=True, blank=True)
	displaytc = models.BooleanField()
	display_comments = models.BooleanField()
	width = models.IntegerField(null=True, blank=True)
	height = models.IntegerField(null=True, blank=True)
	fps = models.FloatField(null=True, blank=True)
	frame_rate = models.CharField(
		max_length=5,
		choices=[
			('30ND', '30 non-drop'),
			('30DF', '30 drop'),
			('24', '24'),
		],
		default='30ND',
	)
	display_size = models.CharField(max_length=1, choices=[('A','Automatic'),('C','Custom')], default='A')
	display_width = models.IntegerField(null=True, blank=True)
	display_height = models.IntegerField(null=True, blank=True)
	thumb = models.ImageField(upload_to='/', null=True, blank=True)
	edl = models.FileField(upload_to='/', null=True, blank=True)
	digest = models.CharField(max_length=32)
	
	project = models.CharField(max_length=256, null=True, blank=True)
	logger = models.CharField(max_length=256, null=True, blank=True)
	date_shot = models.DateField(null=True, blank=True)
	date_logged = models.DateField(null=True, blank=True)
	tape_format = models.CharField(max_length=3, choices=settings.TAPE_FORMAT_CHOICES, blank=True)
	
	timecode_display = models.CharField(max_length=3, choices=settings.TC_TRACKS, default=settings.TC_TRACKS[0][0])
	error = models.IntegerField(null=True, blank=True)
	site = models.ForeignKey(Site)
	
	objects = models.Manager()
	on_site = CurrentSiteManager()

	def __str__(self):
		return "%s" % str(self.name)
	
	def get_file_path(self):
		return os.path.join(settings.UPLOAD_ROOT, self.file.name)
	
	def get_file_url(self):
		return settings.UPLOAD_URL + self.file.name

	def get_player_settings(self):
		scale = 'tofit'
		if self.display_size == 'A':
			scale = '1'
		return {
			'url': self.get_file_url(),
			'width': self.get_display_width(),
			'height': self.get_display_height(),
			'autoplay': str(current_site.info.autoplay_videos),
			'scale': scale,
			'timecode': self.displaytc,
		}
	
	def get_error_message(self):
		if self.error == 101:
			return "This video has a bad filename.  It should only contain letters, numbers, underscores, dashes, and periods."

	def get_tc_calc(self):
		if self.edl:
			edl_fp = open(self.edl.path, 'r')
			edl = minjson.read(edl_fp.read()[10:])
			edl_fp.close()
			return tc.TcCalc(edl=edl)
			#if self.display_timecode == 'SRC':
			#	return tc.TcCalc(edl=edl)
			#return tc.TcCalc(start_tc=edl[0]['seqin'])
		return tc.TcCalc(start_tc=self.starttc)
	
	def delim(self):
		return self.starttc[2]
	def tcformat(self):
		if self.delim() == ':':
			return 'nondrop'
		return 'drop'
	
	def get_fps(self):
		if self.frame_rate in ['30ND', '30DF']:
			return 30
		return int(self.frame_rate)
	
	def tc_tracks(self):
		tc_tracks = list(settings.TC_TRACKS)
		if not self.edl: tc_tracks.pop(1)
		return tc_tracks
	
	def get_url(self, playlist_path=None):
		if playlist_path:
			return reverse('flow_playlist_media', args=[playlist_path, self.id, self.name])
		return reverse('flow_media', args=[self.id, self.name])
	
	def get_thumbsize_file(self, size):
		fn = ""
		try:
			fn = self.thumb.file
			fn = fn.replace('thumb', 'thumb'+str(size), 1)
			fn = fn.replace('/media/', '/media/uploads/', 1)
		except:
			pass
		return fn
	def get_thumbsize_url(self, size):
		fn = ""
		try:
			fn = self.thumb.url
			fn = fn.replace('thumb', 'thumb'+str(size), 1)
			fn = fn.replace('/media/', '/media/uploads/', 1)
		except:
			pass
		return fn
	
	def get_thumb64_url(self): return self.get_thumbsize_url(64)
	def get_thumb32_url(self): return self.get_thumbsize_url(32)
	
	def get_destfn(self):
		return os.path.splitext(os.path.basename(self.get_file_path()))[0]
	
	def get_display_width(self):
		if self.display_size == 'C' and self.display_width:
			return self.display_width
		return self.width
	
	def get_display_height(self, width=None):
		if width:
			return int(width*(self.get_display_height()*1.0/self.get_display_width()))
		if self.display_size == 'C' and self.display_height:
			return self.display_height
		return self.height

	def download_encode(media):
		tc = map(int, media.starttc.split(media.delim()))
		start_frame = (tc[0]*60*60*media.fps) + (tc[1]*60*media.fps) + (tc[2]*media.fps) + tc[3]
		w = media.width; h = media.height
		pad = (0, 0, 0, 0) # (top, bottom, left, right)
		if w > h:
			w = w/16*16
			h = media.height*(w/media.height)
			pad = (w*(float(3)/float(4)))-h
			pad[0] = pad/2
			pad[1] = pad[0]
			if pad%2 == 1:
				pad[0] = pad[0]+1
				
		media.download = media.newFile('download')
		cmd = "%(ffmpeg)s -i %(input)s -y -acodec libfaac -ab 128k -vcodec libxvid -b 300k -flags -ac 1 -ar 48000 -r %(fps).0f -vhook '%(drawtext)s -f %(font)s -F -r %(fps).0f -S 16 -s %(start_frame)d -b' -qmin 2 -qmax 5 -title '%(title)s' -s %(w)dx%(h)d -padtop %(padtop)s -padbottom %(padbottom)s -padleft %(padleft)s -padright %(padright)s %(output)s" % {
			'ffmpeg': settings.FFMPEG_BIN,
			'drawtext': settings.DRAWTEXT,
			'input': media.get_file_path(),
			'fps': media.fps,
			'font': os.path.join(settings.INCLUDE_ROOT, 'LucidaConsole.ttf'),
			'start_frame': start_frame,
			'output': media.get_download_filename(),
			'w': w,
			'h': h,
			'title': media.title.replace("'", "\'"),
			'padtop': pad[0],
			'padbottom': pad[1],
			'padleft': pad[2],
			'padright': pad[3],
		}
		raise
		os.system(cmd)
		media.save()
	
	@staticmethod
	def ffmpegImageGrab(videofn, imagefn, size=(320,240), offset=0):
		cmd = '%s -i %s -an -t 1 -r 1 -y -s %dx%d -f image2 -ss %s %s' % (
			settings.FFMPEG_BIN,
			videofn,
			size[0],
			size[1],
			str(offset),
			imagefn,
		)
		# to do: keep aspect ratio using black background
		os.system(cmd)
	
	@staticmethod
	def randStr(playlist, name):
		return '_'.join([playlist, name, random_string(5)])
	
	def tempBasename(self, prefix='', extension=''):
		basename = os.path.splitext( self.file.name )[0].replace('/', '_')
		basename = Media.path(prefix, '_'.join([prefix, basename, random_string(5)]) + extension)
		return basename

	def importEDL(self, content, filename):
		
		sequence_delim = ''
		source_delim = ''
		edits = []
		
		tcformats = {
			'NON-DROP':':',
			'DROP':';',
		}
		
		tcformat_re = re.compile('^FCM: (DROP|NON-DROP) FRAME')
		edit_re = re.compile('^\d\d\d\s+(\w+).*(\d\d:\d\d:\d\d:\d\d)\s+(\d\d:\d\d:\d\d:\d\d)\s+(\d\d:\d\d:\d\d:\d\d)\s+(\d\d:\d\d:\d\d:\d\d)')
		clipname_re = re.compile('^\* FROM CLIP NAME:\s+(.+)')
		
		#f = open(edl_filename, 'r')
		f = content.split('\n')
		for line in f:
			line = line.strip()
			tcformat_match = tcformat_re.match(line)
			if tcformat_match:
				if not sequence_delim:
					sequence_delim = tcformats[tcformat_match.group(1)]
				else:
					source_delim = tcformats[tcformat_match.group(1)]
			edit_match = edit_re.match(line)
			if edit_match:
				if not source_delim: source_delim = ':'
				if not sequence_delim: sequence_delim = ':'
				edits.append({
					'src': re.sub('_', ' ', edit_match.group(1)),
					'srcin': re.sub(':', source_delim, edit_match.group(2)),
					'srcout': re.sub(':', source_delim, edit_match.group(3)),
					'seqin': re.sub(':', sequence_delim, edit_match.group(4)),
					'seqout': re.sub(':', sequence_delim, edit_match.group(5)),
				})
			clipname_match = clipname_re.match(line)
			if clipname_match:
				edits[-1]['srcname'] = clipname_match.group(1)

		json = "var edl = " + minjson.write(edits)
		
		fn = Media.path('edl', '_'.join([os.path.basename(filename), random_string(5)]) + '.js')
		self.edl = fn
		f = open(self.edl.path, 'w')
		f.write(json)
		f.close()
		self.save()

	def get_edl_date(self):
		if not self.edl: return ''
		statinfo = os.stat(self.edl.path)
		return datetime.fromtimestamp(statinfo.st_ctime)
	
	def get_edl_origname(self):
		if not self.edl: return ''
		#(basename, ext) = os.path.splitext(self.edl.path)
		#basename = os.path.basename(basename[0:-6])
		#return basename + ext
		return os.path.basename(self.edl.path)[:-9]
	
	@staticmethod
	def path(field, *args):
		hidden_folder = '.drock' + time.strftime('/%Y/%m/%d')
		path = os.path.join({
			'file': '',
			'edl': hidden_folder,
			'thumb': hidden_folder,
			'thumb32': hidden_folder,
			'thumb64': hidden_folder,
			'download': hidden_folder,
		}.get(field, hidden_folder), *args)
		dirname = os.path.dirname(os.path.join(settings.UPLOAD_ROOT, path))
		if not os.path.isdir(dirname):
			os.makedirs(dirname)
		return path
	
	def newFile(media, field):
		ext = {
			'file': '.mov',
			'edl': '.edl',
			'thumb': '.jpg',
			'download': '.mov',
		}[field]
		return os.path.join(Media.path(field), Media.randStr(media.playlist, media.name)+ext)
	
	def sync(self):
		sync_file(self.get_file_path())
	
	class Admin:
		pass
admin.site.register(Media)

class Clip(models.Model):
	media = models.ForeignKey(Media)
	start = models.IntegerField()
	text = models.TextField()
	fts_id = models.IntegerField(null=True)

	objects = models.Manager()
	on_site = CurrentSiteManager('media.site')
	
	def __str__(self):
		return str(self.id) + ' - ' + str(self.start) + ' - ' + self.text
	
	def get_text(self):
		if not self.fts_id: return ''
		db = connection.cursor()
		db.execute('select text from flow_clip_fts where rowid=%s', [self.fts_id])
		return db.fetchone()[0]
	
	def save(self):
		text = self.text
		self.text = ''
		db = connection.cursor()
		if not self.fts_id:
			db.execute('insert into flow_clip_fts (text) values (%s)', [text])
			self.fts_id = db.lastrowid
		else:
			db.execute('update flow_clip_fts set text=%s where rowid=%s', [text, self.fts_id])
		super(Clip, self).save()
		self.text = text
	
	#class Admin:
		#pass
#admin.site.register(Clip)

def get_default_media():
	try:
		return Media.on_site.get(name="__default__")
	except Media.DoesNotExist:
		media = Media(
			name='__default__',
			title='__default__',
			pub_date=datetime.now(),
			duration=0,
			width=320,
			height=240,
			fps=30,
			starttc='01:00:00:00',
			digest='0',
			displaytc=True,
			display_comments=True,
			site_id=Site.objects.get_current().id,
		)
		media.save()
		return get_default_media()

def get_digest(filename):
	si = os.stat(filename)
	return str(si.st_size) + str(si.st_mtime) + str(si.st_ctime)

def get_basename(filename):
	basename = os.path.basename(filename)
	return os.path.splitext(basename)[0]
	
def get_user_playlists(user):
	playlists = []
	if user.is_authenticated():
		playlists += map(lambda x: x.split('.')[-1], user.get_all_permissions())
	return playlists

def search(expr, user):
	playlist_ids = Playlist.have_permission(user).values_list('id', flat=True)
	db = connection.cursor()
	db.execute('select flow_clip.media_id as media_id, flow_clip.id as clip_id from flow_clip_fts, flow_clip, flow_media_playlists where flow_clip.fts_id = flow_clip_fts.rowid and flow_clip_fts.text match %s and flow_clip.media_id = flow_media_playlists.media_id and flow_media_playlists.playlist_id in (' + ','.join(map(str, playlist_ids)) + ')', [expr])
	#sql = 'select flow_clip.media_id as media_id, flow_clip_fts.rowid as clip_id, flow_clip_fts.text as text from flow_clip_fts, flow_clip, flow_media_playlists where flow_clip.fts_id = flow_clip_fts.rowid and flow_clip_fts.text match %s and flow_clip.media_id = flow_media_playlists.media_id and flow_media_playlists.playlist_id in (%s)' % (expr, ','.join(map(str, playlist_ids)))
	return db.fetchall()

def sync_file(filename):
	
	#rel_fn = filename[len(settings.UPLOAD_ROOT)+1:]
	rel_fn = filename[len(settings.UPLOAD_ROOT):]
	
	# if the file does not exist delete media from the database
	if not os.path.exists(filename):
		for media in Media.on_site.filter(file=rel_fn):
			# todo: this should also filter the object_type
			#FreeComment.objects.filter(object_id=media.id).delete()
			try:
				media.delete()
			except IOError:
				pass
		return
	
	# if the file and media exist, check the digest
	current_digest = get_digest(filename)
	medias = Media.on_site.filter(file=filename)
	if medias:
		if medias[0].digest == current_digest:
			return
		else:
			for media in medias: media.digest = current_digest # for migration
			return
			#for media in medias: media.delete()
	
	# if a media already exists at the same path with a different video file extension, do not add it
	name = get_basename(filename)
	for media in Media.on_site.filter(name=name):
		if os.path.splitext(media.get_file_path())[0] == os.path.splitext(filename)[0]:
			return
	
	default_media = get_default_media()

	# The file is new, create a new media entry
	media = Media(
		name=name,
		file = rel_fn,
		title=S(name.replace('_', ' ')).heading(),
		pub_date=datetime.fromtimestamp(os.stat(filename).st_mtime),
		digest=current_digest,
		display_comments=default_media.display_comments,
		site_id = Site.objects.get_current().id,
	)
	media.save()

	# Auto-add to playlist
	playlist_path = os.path.split(rel_fn)[0]
	if not playlist_path: playlist_path = 'home'
	media.playlists.add(Playlist.on_site.get(path=playlist_path))
	
	# file type specifics
	if not re.compile('^[\w\.-]+$').match(name):
		media.error = 101 # bad filename
	
	else:
		# call qt-faststart incase it's needed :)
		#if os.path.splitext(filename)[1] in ['.mov', '.mp4', '.m4v']:
		#	tmpfn = os.path.join(tempfile.gettempdir(), os.path.basename(filename))
		#	if os.path.isfile(tmpfn):
		#		os.remove(tmpfn)
		#	qtfs = popen2.Popen3("%s %s %s" % (settings.QTFS_BIN, filename, tmpfn), True)
		#	line = qtfs.fromchild.read()
		#	if re.compile('copying rest of file...').search(line):
		#		os.remove(filename)
		#		os.rename(tmpfn, filename)
		#		current_digest = get_digest(filename)
		#		pass
	
		fi = ffinfo.ffinfo(filename)
		media.duration = fi.str_duration()
		media.width = fi.size[0]
		media.height = fi.size[1]
		media.fps = fi.fps
		media.starttc = default_media.starttc
		media.displaytc = default_media.displaytc
		
		thumbfn = media.tempBasename('thumb', '.jpg')
		media.thumb = thumbfn
		fn = thumbfn.replace('thumb', 'thumb32', 1)
		Media.ffmpegImageGrab(media.get_file_path(), os.path.join(settings.UPLOAD_ROOT, fn), (32,24), 0)
		fn = thumbfn.replace('thumb', 'thumb64', 1)
		Media.ffmpegImageGrab(media.get_file_path(), os.path.join(settings.UPLOAD_ROOT, fn), (64,48), 0)
		
	media.save()
