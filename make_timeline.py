#!/usr/local/bin/python

import parsedatetime
import svgwrite

import datetime
import json
import sys

def datetime_from_string(cal, s):
    dt, flag = cal.parse(s)
    if flag in (1,2):
        dt = datetime.datetime(*dt[:6])
    else:
    	dt = datetime.datetime(*dt[:6])
    return dt, flag

def estimate_width(callout_size, text):
	return callout_size[0] + 10*len(text)

def create_timeline(filename):
	s = ''
	with open(filename) as f:
		s = f.read()
	data = json.loads(s)
	cal = parsedatetime.Calendar()
	start_date = datetime_from_string(cal, data['start'])
	end_date = datetime_from_string(cal, data['end'])
	total_secs = (end_date[0] - start_date[0]).total_seconds()	
	width = 800
	height = 450
	drawing = svgwrite.Drawing('out.svg', profile='tiny', size=(width, height))
	drawing.add(drawing.line((0, height/2), (width, height/2), stroke="black", stroke_width=3))
	callouts = data['callouts']
	for event, date_string in callouts.iteritems():
		event_date = datetime_from_string(cal, date_string)
		num_sec = (event_date[0] - start_date[0]).total_seconds()
		percent_width = num_sec/total_secs
		if percent_width < 0 or percent_width > 1:
			continue
		x = int(percent_width*width + 0.5)
		callout_size = (25, 50)
		text_fudge = (5, 5)
		drawing.add(drawing.line((x, height/2), (x, height/2 - callout_size[1]), stroke='black', stroke_width=2))
		drawing.add(drawing.line((x, height/2 - callout_size[1]), (x - callout_size[0], height/2 - callout_size[1]), stroke='black', stroke_width=2))		
		drawing.add(drawing.text(event, insert=(x - callout_size[0] - text_fudge[0], height/2 - callout_size[1] + text_fudge[1]), font_family="Helevetica", font_size="10pt", text_anchor="end"))
		drawing.add(drawing.circle((x, height/2), r=5, stroke='black', stroke_width=2, fill='white'))
	drawing.save()

if __name__ == '__main__':
	create_timeline(sys.argv[1])