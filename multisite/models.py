from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User, UserManager, check_password
from django.contrib.auth.admin import UserAdmin
from django.contrib.sites.models import Site
from django.contrib.sites.managers import CurrentSiteManager

from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_model

# Create your models here.

current_site = Site.objects.get_current()

def users_on_site():
	return User.objects.filter(username__startswith=current_site.name+'_')

class SiteInfo(models.Model):
	site = models.OneToOneField(Site, primary_key=True, related_name="info")
	#site = models.ForeignKey(Site)
	name = models.CharField(max_length=10, unique=True)
	theme = models.CharField(
		max_length=30,
		choices = [
			('default', 'default'),
			('mess', 'mess'),
			('b2', 'b2'),
		],
	)
	title = models.CharField(max_length=30, blank=True)
	logotext = models.TextField(blank=True)
	media_root = models.CharField(max_length=100, blank=True)
	enable_secure_playlists = models.BooleanField()
	autoplay_videos = models.BooleanField()
	
	on_site = User.objects.filter(username__startswith=current_site.name+'_')
	
	def __str__(self):
		return str(self.site.domain)
	
	def is_authenticated(self, user):
		if not user.is_authenticated():
			return False
		try:
			(site, username) = user.username.split('_', 1)
		except ValueError:
			return False  # if the user doeen't belong to a site, they're not authenticated as a multisite user
		return site == self.name
	
	def is_staff(self, user):
		return self.is_authenticated(user) and user.is_staff
	
admin.site.register(SiteInfo)

class MultisiteUserModelBackend(ModelBackend):
	
	def authenticate(self, username=None, password=None):
		try:
			if not username == 'admin': # Should be if user is 'admin' and site is 'localhost'
				site = Site.objects.get_current()
				username = site.name + '_' + username
			user = User.objects.get(username=username)
			if user.check_password(password):
				return user
		except User.DoesNotExist:
			return None
	
	def get_user(self, user_id):
		try:
			return User.objects.get(pk=user_id)
		except User.DoesNotExist:
			return None
	
	#@property
	#def user_class(self):
	#	if not hasattr(self, '_user_class'):
	#		self._user_class = get_model(*settings.CUSTOM_USER_MODEL.split('.', 2))
	#		if not self._user_class:
	#			raise ImproperlyConfigured('Could not get muser model')
	#	return self._user_class
