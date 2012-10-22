import math, re
from django.utils.safestring import mark_safe

def parse_offsets(string, media=None):
	track = 'SEQ'
	try:
		if media.edl: track = 'SRC'
	except AttributeError:
		pass
	tc_calc = None
	if media:
		tc_calc = media.get_tc_calc()
	def parser(match):
		tc = match.group(1)
		if tc_calc:
			tc = tc_calc.timecodeFromOffset(int(match.group(1)))
		return '<a onclick="player.setOffset(%s);">%s</a>' % (match.group(1), tc)
	return mark_safe(re.sub('\[ (\d+) \]', parser, string))

def tcToTuple(tc):
	return map(int, tc.split(tc[2]))

def tupleToTc(tc_tuple, d):
	return '%02d%s%02d%s%02d%s%02d' % (tc_tuple[0], d, tc_tuple[1], d, tc_tuple[2], d, tc_tuple[3])

class TcCalc():
	
	def __init__(self, start_tc='', edl=None, fps=30):
		self.start_tc = start_tc
		self.edl = edl
		self.fps = fps
		self.edit_index = 0
	
	def tcToFc(self, tc):
		d = tc[2]
		tc = map(int, tc.split(d))
		return tc[0]*self.fps*3600 + tc[1]*self.fps*60 + tc[2]*self.fps + tc[3]
	
	def fcToTc(self, fc, d=":"):
		return tupleToTc(( math.floor((fc/(self.fps*3600.0))%24), math.floor(fc%(self.fps*3600.0)/(self.fps*60.0)), math.floor(fc%(self.fps*60.0)/self.fps), fc%self.fps ), d)
	
	def offsetToFc(self, offset):
		return math.floor((offset*self.fps)/100.0)
	
	def timecodePlusFc(self, start_tc, offset_fc):
		d = start_tc[2]
		fc = self.tcToFc(start_tc) + offset_fc
		tc = self.fcToTc(fc, d)
		if not (d == ';' and self.fps == 30):
			return tc
		start_tc_tuple = map(int, start_tc.split(d))
		tc_tuple = map(int, tc.split(d))
		if tc_tuple[0] < start_tc_tuple[0]:
			tc_tuple[0] += 24
		minutes_elapsed = ((tc_tuple[0]*60) + tc_tuple[1]) - ((start_tc_tuple[0]*60) + start_tc_tuple[1])
		dropped_frames = ( minutes_elapsed - ((tc_tuple[1]/10) - (start_tc_tuple[1]/10)) ) * 2
		tc = self.fcToTc(fc + dropped_frames, d)
		tc_tuple = map(int, tc.split(d))
		if tc_tuple[3] < 2 and tc_tuple[2] == 0 and tc_tuple[1]%10 != 0:
			tc_tuple[3] = 2
			tc = tupleToTc(tc_tuple, d)
		return tc

	def editFromOffset(self, offset):
		seq_tc = self.timecodePlusFc(self.edl[0]['seqin'], self.offsetToFc(offset))
		i = 0
		while not (seq_tc >= self.edl[self.edit_index]['seqin'] and seq_tc < self.edl[self.edit_index]['seqout']):
			self.edit_index += 1
			if self.edit_index >= len(self.edl):
				self.edit_index = 0
			i += 1
			if i >= len(self.edl):
				return False
		return self.edl[self.edit_index]
	
	def timecodeFromOffset(self, offset):
		if self.edl:
			edit = self.editFromOffset(offset)
			if not edit:
				return str(self.offsetToFc(offset))
			offset_fc = self.offsetToFc(offset) + self.tcToFc(self.edl[0]['seqin']) - self.tcToFc(edit['seqin'])
			return self.timecodePlusFc(edit['srcin'], offset_fc)
		return self.timecodePlusFc(self.start_tc, self.offsetToFc(offset))

	def srcNameFromOffset(self, offset):
		edit = self.editFromOffset(offset)
		if not edit:
			return ''
		return edit['src']
