from django.contrib.sites.models import Site
from django.conf import settings

def site(request):
    """
    Adds site-related context variables to the context.

    """
    return {
		'site': Site.objects.get_current(),
	}
