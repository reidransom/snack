from django.conf import settings
from flow.config import *
import popen2, re

#FFMPEG = "/usr/local/bin/ffmpeg"

class ffinfoError(Exception):
	def __init__(self, msg):
		self.msg = msg
	def __str__(self):
		return self.msg

class ffinfo:
	
	def __init__(self, filename):
		
		self.filename = filename
		self.duration = None
		self.fps = None
		self.size = None
		
		re_duration = re.compile("Duration: (?P<h>\d\d):(?P<m>\d\d):(?P<s>\d\d)\.(?P<r>\d)")
		#re_fps = re.compile("(?P<x>\d\d)\.(?P<y>\d\d) fps\(r\)")
		re_fps = re.compile(", (\d\d\.\d\d) tb\(r\)")
		re_size = re.compile(" (?P<w>\d+)x(?P<h>\d+),")

		ffmpeg = popen2.Popen3("%s -i %s" % (settings.FFMPEG_BIN, filename), True)
		line = ffmpeg.childerr.read()

		match_duration = re_duration.search(line)
		if match_duration:
			self.duration = ( int(match_duration.group("h")), \
							  int(match_duration.group("m")), \
							  int(match_duration.group("s")), \
							  int(match_duration.group("r")) )
		if not self.duration:
			self.duration = (0,0,0,0)

		match_fps = re_fps.search(line)
		fps = 0
		if match_fps:
			#fps = ( int(match_fps.group("x")), int(match_fps.group("y")) )
			self.fps = match_fps.group(1)
		#if fps[1] >= 50:
		#	fps = fps[0] + 1
		#else:
		#	fps = fps[0]
		#self.fps = fps

		match_size = re_size.search(line)
		if match_size:
			self.size = ( int(match_size.group("w")), int(match_size.group("h")) )
		if not self.size:
			self.size = (0,0)

	def get_size(self):
		if not isinstance(self.size, tuple):
			return None
		return self.size

	def get_fps(self):
		if not isinstance(self.fps, tuple):
			return None
		if self.fps[1] >= 50:
			return self.fps[0]+1
		return self.fps[0]

	def get_duration(self):
		if not isinstance(self.duration, tuple):
			return None
		return (3600*self.duration[0]) + (60*self.duration[1]) \
			+ self.duration[2] + (float(self.duration[3])/10)
	
	def str_duration(self):
		if self.duration[0]: return "%d:%02d:%02d.%d" % self.duration
		return "%d:%02d.%d" % self.duration[1:]
	
	def __str__(self):
		return str(self.__dict__)

def get_dimensions(filename):
	info = ffinfo(filename)
	return info.size
