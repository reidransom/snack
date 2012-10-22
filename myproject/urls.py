from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^myproject/', include('myproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^djangoadmin/', include(admin.site.urls)),

    url(r'^signin$', 'django.contrib.auth.views.login', name="flow_login"),
    url(r'^signin_required$', 'django.contrib.auth.views.login', name="flow_login_required"),
    url(r'^playlist/(?P<playlist>\w+)/(?P<id>\d+)/(?P<media>[\w\.-]+)(?:/(?P<view>\w*))?$', 'flow.views.media', name="flow_playlist_media"),
    url(r'^(?P<id>\d+)/(?P<media>[\w\.-]+)(?:/(?P<view>\w*))?$', 'flow.views.media', name="flow_media"),
)
	
urlpatterns += patterns('flow.admin_views',
    (r'^admin/$', 'general'),
    (r'^admin/users$', 'users'),
    (r'^admin/add_user$', 'add_user'),
    (r'^admin/delete_user/(?P<user_id>\d+)$', 'delete_user'),
    (r'^admin/edit_user/(?P<user_id>\d+)$', 'edit_user'),
)

urlpatterns += patterns('flow.views',
    (r'^$', 'index'),
    (r'^feeds/playlist/(?P<playlist>\w+)$', 'feed'),
    (r'^a/(?P<action>\w+)$', 'action'),
    (r'^playlist/(?P<playlist>\w+)(?:/(?P<view>\w*))?$', 'playlist'),
    (r'^(?P<playlist>\w+)/(?P<media>[\w\.-]+)?$', 'playlist_redirect'),
)
