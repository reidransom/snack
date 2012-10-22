from django import forms
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.forms.models import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.safestring import mark_safe
from multisite.models import SiteInfo, current_site
from flow.models import Playlist
from flow.utils import add_session_message

class GeneralSettingsForm(forms.ModelForm):
	title = forms.CharField(required=True)
	logotext = forms.CharField(
		required = False,
		widget = forms.Textarea(attrs={'rows':'3'}),
	)
	class Meta:
		model = SiteInfo
		fields = (
			'title',
			'logotext',
			#'enable_secure_playlists'
			'autoplay_videos',
		)

@user_passes_test(lambda u: u.is_staff)
def general(request):
	
	general_form = None
	if request.POST.get('save', '') == 'Save':
		general_form = GeneralSettingsForm(request.POST, instance=current_site.info)
		try:
			general_form.save()
		except ValueError:
			pass
	else:
		general_form = GeneralSettingsForm(instance=current_site.info)

	return render_to_response(
		'admin/settings.html',
		{
			'view': 'general',
			'general_form': general_form,
		},
		context_instance = RequestContext(request),
	)

@user_passes_test(lambda u: u.is_staff)
def users(request):
	return render_to_response(
		'admin/settings.html',
		{
			'view': 'users',
			'user_list': User.objects.filter(
				username__startswith = current_site.name + '_',
			).order_by('username'),
		},
		context_instance = RequestContext(request),
	)

class AddUserForm(forms.Form):
	username = forms.CharField(max_length=15, min_length=4)
	password = forms.CharField(max_length=15, min_length=6, widget=forms.PasswordInput)
	password_again = forms.CharField(max_length=15, min_length=6, widget=forms.PasswordInput)

@user_passes_test(lambda u: u.is_staff)
def add_user(request):
	add_user_form = None
	if request.method == 'POST':
		add_user_form = AddUserForm(request.POST)
		
		if add_user_form.is_valid():
			
			add_user_form.my_error = None
			username = current_site.name + '_' + add_user_form.cleaned_data['username']
			
			if not add_user_form.cleaned_data['password'] == add_user_form.cleaned_data['password_again']:
				add_user_form.my_error = "Passwords did not match."

			if User.objects.filter(username=username):
				add_user_form.my_error = "Sorry, that username is already taken."
				
			if not add_user_form.my_error:
				u = User.objects.create_user(
					username,
					'',
					add_user_form.cleaned_data['password'],
				)
				return HttpResponseRedirect(reverse('flow.admin_views.users'))
	else:
		add_user_form = AddUserForm()
	return render_to_response(
		'admin/settings.html',
		{
			'view': 'users',
			'add_user_form': add_user_form,
		},
		context_instance = RequestContext(request),
	)

class EditUserForm(forms.ModelForm):
	username = forms.CharField(max_length=15, min_length=3)
	username.filter_value = lambda x: x.split('_')[1]
	password = forms.CharField(max_length=15, min_length=6, required=False, widget=forms.PasswordInput)
	password_again = forms.CharField(max_length=15, min_length=6, required=False, widget=forms.PasswordInput)
	class Meta:
		model = User
		fields = (
			'username',
			'is_staff',
		)

@user_passes_test(lambda u: current_site.info.is_staff(u))
def delete_user(request, user_id):
	user = get_object_or_404(User, id=user_id)
	if user.is_staff and len(current_site.info.on_site.filter(is_staff=True)) < 2:
		add_session_message(request, "%s is the last remaining staff user and therefore cannot be deleted." % user.username.split('_', 1)[1])
		return HttpResponseRedirect(reverse('flow.admin_views.edit_user', args=[user_id]))
	user.delete()
	return HttpResponseRedirect(reverse('flow.admin_views.users'))

@user_passes_test(lambda u: current_site.info.is_staff(u))
def edit_user(request, user_id):
	edit_user_form = None
	user = get_object_or_404(User, id=user_id)

	if request.method == 'POST':
		edit_user_form = EditUserForm(request.POST, instance=user)
		
		if edit_user_form.is_valid():
			edit_user_form.my_error = None
			username = current_site.name + '_' + edit_user_form.cleaned_data['username']
			edit_user_form.cleaned_data['username'] = username
			
			if edit_user_form.cleaned_data['password'] and edit_user_form.cleaned_data['password'] != edit_user_form.cleaned_data['password_again']:
				edit_user_form.my_error = "Passwords did not match."

			if user.username != username and User.objects.filter(username=username):
				edit_user_form.my_error = "Sorry, that username is already taken."
				
			if not edit_user_form.my_error:
				try:
					edit_user_form.save()
					if edit_user_form.cleaned_data['password']:
						user.set_password(edit_user_form.cleaned_data['password'])
						user.save()
					p_set = []
					for id in request.POST.getlist('playlists'):
						p_set.append(get_object_or_404(Playlist, id=id))
					user.playlist_set = p_set
					user.save()
					return HttpResponseRedirect(reverse('flow.admin_views.users'))
				except ValueError:
					pass
	else:
		edit_user_form = EditUserForm(instance=user)
	
	html = '<label for="id_playlists">Playlists</label><select id="id_playlists" name="playlists" multiple="multiple">'
	for pl in Playlist.on_site.all().exclude(path="__default__"):
		selected = ''
		if pl in Playlist.have_permission(user):
			selected = ' selected="selected"'
		html += '<option value="%s"%s>%s</option>' % (pl.id, selected, pl.name)
	html += '</select>'
	edit_user_form.playlists = mark_safe(html)

	return render_to_response(
		'admin/settings.html',
		{
			'view': 'users',
			'edit_user_form': edit_user_form,
			'edit_user': user,
		},
		context_instance = RequestContext(request),
	)
