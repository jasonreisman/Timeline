#!/usr/bin/python
# -*- coding: utf-8 -*-

import parsedatetime
import svgwrite

import datetime
import json
import os.path
import sys

try:
    # for Python2
    import Tkinter
except ImportError:
    # for Python3
    import tkinter as Tkinter

try:
    import tkFont
except ImportError:
    import tkinter.font as tkFont


class Colors:

    black = '#000000'
    gray = '#C0C0C0'


class Leveler():

    def __init__(self, width=10, height=15, increment=10, spacing_x=3):

        # static
        self.width = width
        self.height = height
        self.increment = increment
        self.spacing_x = spacing_x

        # dynamic
        self.x_positions = [float('-inf')]
        self.previous_levels = [-1]

        # storage
        self.min_y = 0

    def __call__(self, x, text_width):

        level = 0
        i = len(self.x_positions) - 1
        left = x - (text_width + self.width + self.spacing_x)

        while left < self.x_positions[i] and i >= 0:
            level = max(level, self.previous_levels[i] + 1)
            i -= 1

        y = 0 - self.height - level * self.increment

        self.min_y = min(self.min_y, y)
        self.previous_levels.append(level)
        self.x_positions.append(x)

        return x, y, level


class Timeline:

    def __init__(self, filename):

        # load timeline data
        s = ''
        with open(filename) as f:
            s = f.read()
        self.data = json.loads(s)
        assert 'width' in self.data, 'width property must be set'
        assert 'start' in self.data, 'start property must be set'
        assert 'end' in self.data, 'end property must be set'

        # create drawing
        self.width = self.data['width']
        self.drawing = svgwrite.Drawing()
        self.drawing['width'] = self.width
        self.svg_groups = {'callouts': self.drawing.g(),
                           'main_axis': self.drawing.g(),
                           'eras': self.drawing.g(),
                           'tick_labels': self.drawing.g(),
                           }

        # figure out timeline boundaries
        self.cal = parsedatetime.Calendar()
        self.date_parsing_format = self.data.get('date_parsing_format', None)
        self.start_date = self.datetime_from_string(self.data['start'])
        self.end_date = self.datetime_from_string(self.data['end'])
        delta = self.end_date - self.start_date
        padding = datetime.timedelta(seconds=0.1 * delta.total_seconds())
        self.date0 = self.start_date - padding
        self.date1 = self.end_date + padding
        self.total_secs = (self.date1 - self.date0).total_seconds()

        # set up some params
        self.callout_size = (10, 15, 10)  # width, height, increment
        self.text_fudge = (3, 1.5)
        self.tick_format = self.data.get('tick_format', None)
        self.markers = {}
        self.ticks = {}

        # initialize Tk so that font metrics will work
        self.tk_root = Tkinter.Tk()
        self.fonts = {}

        # max_label_height stores the max height of all axis labels
        # and is used in the final height computation in build(self)
        self.max_label_height = 0

        # leveler for ticks
        self.tick_leveler = Leveler(0, self.callout_size[1],
            self.callout_size[2], self.text_fudge[0])

    def build(self):

        # MAGIC NUMBER: y_era
        # draw era label and markers at this height
        y_era = 10

        # create main axis and callouts,
        # keeping track of how high the callouts are
        self.create_main_axis()
        y_callouts = self.create_callouts()

        # determine axis position so that axis + callouts
        # don't overlap with eras
        y_axis = y_era + self.callout_size[1] - y_callouts

        # determine height so that eras, callouts, axis, and labels just fit
        height = y_axis + 4 * self.text_fudge[1]

        # create eras and labels using axis height and overall height
        self.create_eras(y_era, y_axis, height)
        self.create_era_axis_labels()

        self.draw_axis_labels()

        # translate the axis group and add it to the drawing
        global_group = self.drawing.g()
        global_group.add(self.svg_groups['tick_labels'])
        global_group.add(self.svg_groups['main_axis'])
        global_group.add(self.svg_groups['callouts'])
        global_group.translate(0, y_axis)

        # eras are not translated -> not in global group
        self.drawing.add(self.svg_groups['eras'])
        self.drawing.add(global_group)

        # finally set the height on the drawing
        self.drawing['height'] = height

    def save(self, filename):
        self.drawing.saveas(filename)

    def to_string(self):
        return self.drawing.tostring()

    def datetime_from_string(self, s):
        if self.date_parsing_format is not None:
            return datetime.datetime.strptime(s, self.date_parsing_format)

        (dt, flag) = self.cal.parse(s)
        return datetime.datetime(*dt[:6])

    def get_strftime(self, ts, fmt):
        # < 1900 Solution found at:
        # https://stackoverflow.com/questions/1526170/formatting-date-string-in-python-for-dates-prior-to-1900
        if ts.year < 1900:
            d = {'%Y': '{0.year}', '%m': '{0.month:02}', '%d': '{0.day:02}',
                 '%H': '{0.hour:02}', '%S': '{0.second:02}', '%M': '{0.minute:02}',
                 '%YY': '{0.year:04}'}
            for s, r in sorted(d.items(), reverse=True):
                fmt = fmt.replace(s, r)
            return fmt.format(ts)
        else:
            return ts.strftime(fmt)

    def create_eras(self, y_era, y_axis, height):
        if 'eras' not in self.data:
            return

        # create eras
        eras_data = self.data['eras']
        markers = {}
        for era in eras_data:

            # extract era data
            name = era[0]
            t0 = self.datetime_from_string(era[1])
            t1 = self.datetime_from_string(era[2])
            fill = (era[3] if len(era) > 3 else Colors.gray)

            # get marker objects
            (start_marker, end_marker) = self.get_markers(fill)
            assert start_marker is not None
            assert end_marker is not None

            # create boundary lines
            percent_width0 = (t0 - self.date0).total_seconds() \
                / self.total_secs
            percent_width1 = (t1 - self.date0).total_seconds() \
                / self.total_secs
            x0 = int(percent_width0 * self.width + 0.5)
            x1 = int(percent_width1 * self.width + 0.5)
            rect = self.svg_groups['eras'].add(self.drawing.rect((x0, 0), (x1 - x0,
                                                                height)))
            rect.fill(fill, None, 0.15)
            line0 = self.svg_groups['eras'].add(self.drawing.line((x0, 0), (x0, y_axis),
                                                       stroke=fill,
                                                       stroke_width=0.5))
            line1 = self.svg_groups['eras'].add(self.drawing.line((x1, 0), (x1, y_axis),
                                                       stroke=fill,
                                                       stroke_width=0.5))
            line1.dasharray([5, 5])
            line0.dasharray([5, 5])

            # create horizontal arrows and text
            self.svg_groups['eras'].add(self.drawing.line((x0, y_era), (x1, y_era),
                                               stroke=fill,
                                               stroke_width=0.75))
            self.svg_groups['eras'].add(self.drawing.text(
                name,
                insert=(0.5 * (x0 + x1), y_era - self.text_fudge[1]),
                stroke='none',
                fill=fill,
                font_family='Helevetica',
                font_size='6pt',
                text_anchor='middle',
                ))

    def get_markers(self, color):

        # create or get marker objects
        (start_marker, end_marker) = (None, None)
        if color in self.markers:
            (start_marker, end_marker) = self.markers[color]
        else:
            start_marker = self.drawing.marker(insert=(0, 3), size=(10, 10),
                                               orient='auto')
            start_marker.add(self.drawing.path('M6,0 L6,7 L0,3 L6,0',
                             fill=color))
            self.drawing.defs.add(start_marker)
            end_marker = self.drawing.marker(insert=(6, 3), size=(10, 10),
                                             orient='auto')
            end_marker.add(self.drawing.path('M0,0 L0,7 L6,3 L0,0',
                           fill=color))
            self.drawing.defs.add(end_marker)
            self.markers[color] = (start_marker, end_marker)
        return (start_marker, end_marker)

    def create_main_axis(self):

        # draw main line
        self.svg_groups['main_axis'].add(self.drawing.line((0, 0),
                                         (self.width, 0),
                                         stroke=Colors.black, stroke_width=3))

        # add tickmarks

        self.add_axis_label(self.start_date, str(self.start_date), tick=True)
        self.add_axis_label(self.end_date, str(self.end_date), tick=True)

        if 'num_ticks' in self.data:
            delta = self.end_date - self.start_date
            secs = delta.total_seconds()
            num_ticks = self.data['num_ticks']
            for j in range(1, num_ticks):
                tick_delta = datetime.timedelta(seconds=j * secs / num_ticks)
                tickmark_date = self.start_date + tick_delta
                self.add_axis_label(tickmark_date,
                                    str(tickmark_date), tick=True)

    def create_era_axis_labels(self):
        if 'eras' not in self.data:
            return
        eras_data = self.data['eras']
        for era in eras_data:

            # extract era data
            t0 = self.datetime_from_string(era[1])
            t1 = self.datetime_from_string(era[2])

            # add marks on axis

            self.add_axis_label(t0, str(t0), tick=False, fill=Colors.black)
            self.add_axis_label(t1, str(t1), tick=False, fill=Colors.black)

    def get_starting_postion(self, dt):
        percent_width = (dt - self.date0).total_seconds() / self.total_secs
        if percent_width < 0 or percent_width > 1:
            return -1
        return int(percent_width * self.width + 0.5)

    def add_axis_label(self, dt, label, **kwargs):
        if self.tick_format:
            label = self.get_strftime(dt, self.tick_format)

        x = self.get_starting_postion(dt)
        if x < 0:
            return

        dy = 5

        # add tick on line
        add_tick = kwargs.get('tick', True)
        if add_tick:
            stroke = kwargs.get('stroke', Colors.black)
            self.svg_groups['main_axis'].add(self.drawing.line((x, -dy),
                                                               (x, dy),
                                             stroke=stroke, stroke_width=2))

        # add label
        fill = kwargs.get('fill', Colors.gray)

        self.ticks[(label, x)] = fill

    def draw_axis_labels(self):
        min_y = 0
        writing_mode = self.data.get('tick_orientation', 'tb')

        ticks = [list(tup) + [fill] for tup, fill in self.ticks.items()]
        sorted_ticks = sorted(ticks, key=lambda tup: tup[1])

        for tick in sorted_ticks:
            (label, x, fill) = tick
            text_width, text_height = self.get_text_metrics('Helevetica', 6,
                                                            label)

            if writing_mode == 'tb':
                transform = 'rotate(180, %i, 0)' % x
                y = 10
            else:
                transform = 'translate(%i, 0)' % int(text_width / 2)
                (x, y, level) = self.tick_leveler(x, text_width)

            self.svg_groups['tick_labels'].add(self.drawing.text(
                label,
                insert=(x, -y),
                stroke='none',
                fill=fill,
                font_family='Helevetica',
                font_size='6pt',
                text_anchor='end',
                writing_mode=writing_mode,
                transform=transform,
                ))

            if level > 0:
                line = self.drawing.line((x, 0),
                                         (x, -y - text_height),
                                         stroke=fill,
                                         stroke_width=0.75)
                tick = self.svg_groups['tick_labels'].add(line)
                tick.dasharray([3, 3])

            h = text_width + y
            self.max_label_height = max(self.max_label_height, h, y)

        return


    def create_callouts(self):
        min_y = float('inf')
        if 'callouts' not in self.data:
            return 0
        callouts_data = self.data['callouts']

        # sort callouts
        sorted_dates = []
        inv_callouts = {}
        for callout in callouts_data:
            event = callout[0]
            event_date = self.datetime_from_string(callout[1])
            event_color = (callout[2] if len(callout) > 2 else Colors.black)
            sorted_dates.append(event_date)
            if event_date not in inv_callouts:
                inv_callouts[event_date] = []
            inv_callouts[event_date].append((event, event_color))
        sorted_dates.sort()

        get_level = Leveler(*self.callout_size, spacing_x=self.text_fudge[0])

        # add callouts, one by one, making sure they don't overlap
        for event_date in sorted_dates:
            (event, event_color) = inv_callouts[event_date].pop()
            text_width = self.get_text_metrics('Helevetica', 6, event)[0]

            x = self.get_starting_postion(event_date)
            if x < 0:
                continue

            # figure out what 'level' to make the callout on
            (x, y, _) = get_level(x, text_width)

            path_data = 'M{x},0 L{x},{y} L{start},{y}'.format(
                x=int(x),
                y=int(y),
                start=int(x - self.callout_size[0])
                )

            self.svg_groups['callouts'].add(self.drawing.path(path_data,
                                            stroke=event_color,
                                            stroke_width=1,
                                            fill='none'))
            self.svg_groups['callouts'].add(self.drawing.text(
                event,
                insert=(x - self.callout_size[0] - self.text_fudge[0],
                        y + self.text_fudge[1]),
                stroke='none',
                fill=event_color,
                font_family='Helevetica',
                font_size='6pt',
                text_anchor='end',
                ))
            self.add_axis_label(event_date, str(event_date),
                                tick=False, fill=Colors.black)
            self.svg_groups['callouts'].add(self.drawing.circle((x, 0), r=4,
                            stroke=event_color, stroke_width=1,
                            fill='white'))

        return get_level.min_y

    def get_text_metrics(self, family, size, text):
        font = None
        key = (family, size)
        if key in self.fonts:
            font = self.fonts[key]
        else:
            font = tkFont.Font(family=family, size=size)
            self.fonts[key] = font
        assert font is not None
        (w, h) = (font.measure(text), font.metrics('linespace'))
        return (w, h)


def usage():
    print('Usage: ./make_timeline.py in.json > out.svg')
    sys.exit(-1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('missing input filename')
        usage()
    filename = sys.argv[1]
    if not os.path.isfile(filename):
        print('file %s not found' % filename)
        sys.exit(-1)
    timeline = Timeline(filename)
    timeline.build()
    print(timeline.to_string().encode('utf-8'))
