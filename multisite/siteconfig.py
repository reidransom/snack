from django.contrib.sites.models import Site
from djblets.siteconfig.models import SiteConfiguration

def load_site_config():
	"""Sets up the SiteConfiguration, provides defaults and syncs settings."""
	try:
		siteconfig = SiteConfiguration.objects.get_current()
	except SiteConfiguration.DoesNotExist:
		siteconfig = SiteConfiguration(
			site = Site.objects.get_current(),
			version = "1.0",
		)
	#siteconfig.set('site_media_root')

load_site_config()
