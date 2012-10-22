from os.path import basename
import re, random
from django.utils.safestring import mark_safe

class S(str):
	def heading(self):
		"""Only capitalize the first letter of a word if the word in all
		lowercase alpha characters and has more than one character."""
		def parser(match):
			return match.group(1)+match.group(2).title()
		return re.sub('(^|\s|-|_)([a-z]{2,})(?=\s|$|-|_)', parser, self).replace('_',' ')

def random_string(length):
	return ''.join(random.sample('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', length))
