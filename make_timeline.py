#!/usr/local/bin/python

import parsedatetime
import svgwrite

import datetime
import json
import sys

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
		self.text_fudge = (5, 5)

	def build(self):
		self.create_main_axis()
		self.create_callouts()

	def save(self, filename):
		self.drawing.saveas(filename)

	def datetime_from_string(self, s):
	    dt, flag = self.cal.parse(s)
	    if flag in (1,2):
	        dt = datetime.datetime(*dt[:6])
	    else:
	    	dt = datetime.datetime(*dt[:6])
	    return dt, flag

	def create_main_axis(self):
		# draw main line
		y = self.height/2
		self.drawing.add(self.drawing.line((0, y), (self.width, y), stroke="black", stroke_width=3))
		# add tickmarks
		self.add_tickmark(self.start_date, str(self.start_date[0]))
		self.add_tickmark(self.end_date, str(self.end_date[0]))
		if 'num_ticks' in self.data:
			delta = self.end_date[0] - self.start_date[0]
			secs = delta.total_seconds()
			num_ticks = self.data['num_ticks']
			for j in range(1, num_ticks):
				tick_delta = datetime.timedelta(seconds=j*secs/num_ticks)
				tickmark_date = self.start_date[0] + tick_delta
				self.add_tickmark([tickmark_date], str(tickmark_date))	

	def add_tickmark(self, dt, label):
		percent_width = (dt[0] - self.date0).total_seconds()/self.total_secs
		if percent_width < 0 or percent_width > 1:
			return
		x = int(percent_width*self.width + 0.5)
		y = self.height/2
		dy = 5
		# add tick on line
		self.drawing.add(self.drawing.line((x,y-dy), (x,y+dy), stroke='black', stroke_width=2))
		# add label
		gray = "rgb(192, 192, 192)"
		transform = "rotate(180, %i, %i)" % (x, y)
		self.drawing.add(self.drawing.text(label, insert=(x, y-2*dy), stroke='none', fill=gray, font_family="Helevetica", font_size="8pt", text_anchor="end", writing_mode="tb", transform=transform))			

	def create_callouts(self):
		callouts = self.data['callouts']
		# sort callouts
		sorted_dates = []
		inv_callouts = {}
		for event, date_string in callouts.iteritems():
			event_date = self.datetime_from_string(date_string)
			sorted_dates.append(event_date)
			inv_callouts[event_date] = event
		sorted_dates.sort()		
		# add callouts, one by one, making sure they don't overlap
		prev_x = [float('-inf')]
		prev_level = [-1]
		for event_date in sorted_dates:
			event = inv_callouts[event_date]
			num_sec = (event_date[0] - self.date0).total_seconds()
			percent_width = num_sec/self.total_secs
			if percent_width < 0 or percent_width > 1:
				continue
			x = int(percent_width*self.width + 0.5)
			# figure out what "level" to make the callout on 
			k = 0
			i = len(prev_x) - 1
			left = x - self.estimate_width(event)
			while left < prev_x[i] and i >= 0:
				k = max(k, prev_level[i] + 1)
				i -= 1
			y = self.height/2 - self.callout_size[1] - k*self.callout_size[2]
			#drawing.add(drawing.circle((left, y), stroke='red', stroke_width=2))		
			self.drawing.add(self.drawing.line((x, self.height/2), (x, y), stroke='black', stroke_width=2))
			self.drawing.add(self.drawing.line((x+1, y), (x - self.callout_size[0], y), stroke='black', stroke_width=2))		
			self.drawing.add(self.drawing.text(event, insert=(x - self.callout_size[0] - self.text_fudge[0], y + self.text_fudge[1]), font_family="Helevetica", font_size="10pt", text_anchor="end"))
			self.add_label(event_date, str(event_date[0]))
			self.drawing.add(self.drawing.circle((x, self.height/2), r=5, stroke='black', stroke_width=2, fill='white'))
			prev_x.append(x)
			prev_level.append(k)

	def estimate_width(self, text):
		return self.callout_size[0] + self.text_fudge[0] + 7.5*len(text)

	def add_label(self, dt, label):
		percent_width = (dt[0] - self.date0).total_seconds()/self.total_secs
		if percent_width < 0 or percent_width > 1:
			return
		x = int(percent_width*self.width + 0.5)
		y = self.height/2
		dy = 5
		# add label
		transform = "rotate(180, %i, %i)" % (x, y)
		self.drawing.add(self.drawing.text(label, insert=(x, y-2*dy), stroke='none', fill='black', font_family="Helevetica", font_size="8pt", text_anchor="end", writing_mode="tb", transform=transform))			

if __name__ == '__main__':
#	create_timeline(sys.argv[1])
	timeline = Timeline(sys.argv[1])
	timeline.build()
	timeline.save('out.svg')
