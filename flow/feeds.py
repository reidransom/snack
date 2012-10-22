from django.contrib.syndication.feeds import Feed, FeedDoesNotExist
from django.conf import settings
from flow import models

class PlaylistFeed(Feed):
	
	def get_object(self, bits):
		if len(bits) != 1:
			raise ObjectDoesNotExist
		return models.Playlist.get(path=bits[0])
	
	def title(self, playlist):
		#return settings.SITE_TITLE + ' | ' + playlist.name
		return playlist.name
	
	def link(self, playlist):
		if not playlist:
			raise FeedDoesNotExist
		return playlist.get_absolute_url()
	
	def description(self, playlist):
		return playlist.description
	
	def items(self, playlist):
		return playlist.media_set.all().order_by('-pub_date')
	
	def item_link(self, media):
		return media.db_url()
