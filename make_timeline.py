#!/usr/local/bin/python

import parsedatetime
import svgwrite

import datetime
import json
import os.path
import sys

class Colors:
	black = '#000000'
	gray = '#C0C0C0'

class Timeline:
	def __init__(self, filename):
		# load timeline data
		s = ''
		with open(filename) as f:
			s = f.read()
		self.data = json.loads(s)
		# create drawing
		self.width = self.data['width']
		self.height = self.data['height']
		self.drawing = svgwrite.Drawing('out.svg', size=(self.width, self.height))
		# figure out timeline boundaries
		self.cal = parsedatetime.Calendar()
		self.start_date = self.datetime_from_string(self.data['start'])
		self.end_date = self.datetime_from_string(self.data['end'])
		delta = self.end_date[0] - self.start_date[0]
		padding = datetime.timedelta(seconds=0.1*delta.total_seconds())
		self.date0 = self.start_date[0] - padding
		self.date1 = self.end_date[0] + padding
		self.total_secs = (self.date1 - self.date0).total_seconds()	
		# set up some params
		self.callout_size = (25, 50, 25) # width, height, increment
		self.text_fudge = (3, 4)

	def build(self):
		self.create_eras()
		self.create_main_axis()
		self.create_era_axis_labels()
		self.create_callouts()

	def save(self, filename):
		self.drawing.saveas(filename)

	def to_string(self):
		return self.drawing.tostring()

	def datetime_from_string(self, s):
	    dt, flag = self.cal.parse(s)
	    if flag in (1,2):
	        dt = datetime.datetime(*dt[:6])
	    else:
	    	dt = datetime.datetime(*dt[:6])
	    return dt, flag

	def create_eras(self):
		if 'eras' not in self.data:
			return
		# create eras
		eras_data = self.data['eras']
		for era in eras_data:
			# extract era data
			name = era[0]
			t0 = self.datetime_from_string(era[1])
			t1 = self.datetime_from_string(era[2])
			fill = era[3] if len(era) > 3 else Colors.gray
			# create a marker objects
			start_marker = self.drawing.marker(insert=(0,3), size=(10,10), orient='auto')
			start_marker.add(self.drawing.path("M6,0 L6,7 L0,3 L6,0", fill=fill))
			self.drawing.defs.add(start_marker)
			end_marker = self.drawing.marker(insert=(6,3), size=(10,10), orient='auto')
			end_marker.add(self.drawing.path("M0,0 L0,7 L6,3 L0,0", fill=fill))
			self.drawing.defs.add(end_marker)
			# create boundary lines
			percent_width0 = (t0[0] - self.date0).total_seconds()/self.total_secs
			percent_width1 = (t1[0] - self.date0).total_seconds()/self.total_secs
			x0 = int(percent_width0*self.width + 0.5)
			x1 = int(percent_width1*self.width + 0.5)
			rect = self.drawing.add(self.drawing.rect((x0, 0), (x1-x0, self.height/2)))
			rect.fill(fill, None, 0.15)	
			line0 = self.drawing.add(self.drawing.line((x0,0), (x0, self.height/2), stroke=fill, stroke_width=1))
			line0.dasharray([5, 5])
			line1 = self.drawing.add(self.drawing.line((x1,0), (x1, self.height/2), stroke=fill, stroke_width=1))
			line1.dasharray([5, 5])
			# create horizontal arrows and text
			y = self.height/16
			horz = self.drawing.add(self.drawing.line((x0,y), (x1, y), stroke=fill, stroke_width=1))
			horz['marker-start'] = start_marker.get_funciri()
			horz['marker-end'] = end_marker.get_funciri()
			self.drawing.add(self.drawing.text(name, insert=(0.5*(x0 + x1), y - self.text_fudge[1]), stroke='none', fill=fill, font_family="Helevetica", font_size="8pt", text_anchor="middle"))
			# # add marks on axis
			# self.add_axis_label(t0, str(t0[0]), tick=False, fill=Colors.black)
			# self.add_axis_label(t1, str(t1[0]), tick=False, fill=Colors.black)			

	def create_main_axis(self):
		# draw main line
		y = self.height/2
		self.drawing.add(self.drawing.line((0, y), (self.width, y), stroke=Colors.black, stroke_width=3))
		# add tickmarks
		self.add_axis_label(self.start_date, str(self.start_date[0]), tick=True)
		self.add_axis_label(self.end_date, str(self.end_date[0]), tick=True)
		if 'num_ticks' in self.data:
			delta = self.end_date[0] - self.start_date[0]
			secs = delta.total_seconds()
			num_ticks = self.data['num_ticks']
			for j in range(1, num_ticks):
				tick_delta = datetime.timedelta(seconds=j*secs/num_ticks)
				tickmark_date = self.start_date[0] + tick_delta
				self.add_axis_label([tickmark_date], str(tickmark_date), tick=True)	

	def create_era_axis_labels(self):
		if 'eras' not in self.data:
			return
		eras_data = self.data['eras']
		for era in eras_data:
			# extract era data
			t0 = self.datetime_from_string(era[1])
			t1 = self.datetime_from_string(era[2])
			# add marks on axis
			self.add_axis_label(t0, str(t0[0]), tick=False, fill=Colors.black)
			self.add_axis_label(t1, str(t1[0]), tick=False, fill=Colors.black)			

	def add_axis_label(self, dt, label, **kwargs):
		percent_width = (dt[0] - self.date0).total_seconds()/self.total_secs
		if percent_width < 0 or percent_width > 1:
			return
		x = int(percent_width*self.width + 0.5)
		y = self.height/2
		dy = 5
		# add tick on line
		add_tick = kwargs.get('tick', True)
		if add_tick:
			stroke = kwargs.get('stroke', Colors.black)
			self.drawing.add(self.drawing.line((x,y-dy), (x,y+dy), stroke=stroke, stroke_width=2))
		# add label
		fill = kwargs.get('fill', Colors.gray)
		transform = "rotate(180, %i, %i)" % (x, y)
		self.drawing.add(self.drawing.text(label, insert=(x, y-2*dy), stroke='none', fill=fill, font_family='Helevetica', font_size='6pt', text_anchor='end', writing_mode='tb', transform=transform))			

	def create_callouts(self):
		if 'callouts' not in self.data:
			return
		callouts_data = self.data['callouts']
		# sort callouts
		sorted_dates = []
		inv_callouts = {}
		for callout in callouts_data:
			event = callout[0]
			event_date = self.datetime_from_string(callout[1])
			event_color = callout[2] if len(callout) > 2 else Colors.black
			sorted_dates.append(event_date)
			inv_callouts[event_date] = (event, event_color)
		sorted_dates.sort()		
		# add callouts, one by one, making sure they don't overlap
		prev_x = [float('-inf')]
		prev_level = [-1]
		for event_date in sorted_dates:
			event, event_color = inv_callouts[event_date]
			num_sec = (event_date[0] - self.date0).total_seconds()
			percent_width = num_sec/self.total_secs
			if percent_width < 0 or percent_width > 1:
				continue
			x = int(percent_width*self.width + 0.5)
			# figure out what 'level" to make the callout on 
			k = 0
			i = len(prev_x) - 1
			left = x - self.estimate_width(event)
			while left < prev_x[i] and i >= 0:
				k = max(k, prev_level[i] + 1)
				i -= 1
			y = self.height/2 - self.callout_size[1] - k*self.callout_size[2]
			#drawing.add(drawing.circle((left, y), stroke='red', stroke_width=2))		
			path_data = 'M%i,%i L%i,%i L%i,%i' % (x, self.height/2, x, y, x - self.callout_size[0], y)
			self.drawing.add(self.drawing.path(path_data, stroke=event_color, stroke_width=1, fill='none'))
			self.drawing.add(self.drawing.text(event, insert=(x - self.callout_size[0] - self.text_fudge[0], y + self.text_fudge[1]), stroke='none', fill=event_color, font_family='Helevetica', font_size='8pt', text_anchor='end'))
			self.add_axis_label(event_date, str(event_date[0]), tick=False, fill=Colors.black)
			self.drawing.add(self.drawing.circle((x, self.height/2), r=5, stroke=event_color, stroke_width=1, fill='white'))
			prev_x.append(x)
			prev_level.append(k)

	def estimate_width(self, text):
		return self.callout_size[0] + self.text_fudge[0] + 7.5*len(text)

def usage():
	print 'Usage: ./make_timeline.py <in filename> > <out filename>'
	sys.exit(-1)

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print 'missing input filename'
		usage()
	filename = sys.argv[1]
	if not os.path.isfile(filename):
		print 'file %s not found' % filename
		sys.exit(-1)
	timeline = Timeline(sys.argv[1])
	timeline.build()
	print timeline.to_string()
