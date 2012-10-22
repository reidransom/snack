from django import template

register = template.Library()

@register.filter
def shortname(self):
	try:
		return self.split('_', 1)[1]
	except IndexError:
		return self
