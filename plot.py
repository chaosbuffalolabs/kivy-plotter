import kivy
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, BooleanProperty, ListProperty, StringProperty, ObjectProperty, DictProperty
from kivy.graphics import Line, Color, PushMatrix, PopMatrix, Translate, InstructionGroup, Rectangle, Rotate
from kivy.uix.scatter import Scatter
from kivy.lang import Builder
from kivy.uix.label import Label
from math import atan2, sin, cos

def drange(start, stop, step):
    r = start
    while r < stop:
        yield r
        r += step

class Arrow(InstructionGroup):
    def __init__(self, points, line_width = 1, head_length = 8, **kwargs):
        super(Arrow, self).__init__(**kwargs)
        self.add(Line(points=points, width=line_width))
        for p in self.get_head_line_points(points, head_length):
            self.add(Line(points=p, width=line_width))

    def get_head_line_points(self, points, head_length):
        xd = points[0] - points[2]
        yd = points[1] - points[3]
        t = atan2(yd, xd)
        # return the angle between point2 and point1 with a variance of 30 degrees on each side
        head_angles = (t-0.5, t+0.5)
        for th in head_angles:
            yield [points[2], points[3], points[2] + head_length * cos(th), points[3] + head_length * sin(th)]

class ArrowList(Widget):
    begin_series = ObjectProperty(None)
    end_series = ObjectProperty(None)
    x_ranges = ListProperty(None)
    arrow_color = ListProperty([.8, .8 ,.8, .75])
    enabled = BooleanProperty(False)

    def __init__(self, begin_series, end_series, x_ranges, **kwargs):
        self.begin_series = begin_series
        self.end_series = end_series
        self.x_ranges = x_ranges
        assert begin_series.plot == end_series.plot
        self.plot = begin_series.plot

        super(ArrowList, self).__init__(**kwargs)
        
        self.arrows = InstructionGroup()
        self.arrows_translate = Translate()
        self.canvas.add(self.arrows)

        self.pos = self.plot.pos
        self.size = self.plot.size
        self.plot.bind(size = self._set_size)
        self.plot.bind(pos = self._set_pos)
        self.plot.bind(viewport = self.draw)

        self.begin_series.bind(data = self.draw)
        self.end_series.bind(data = self.draw)

        self.bind(x_ranges = self.draw)

    def enable(self):
        if self.enabled:
            return
        self.enabled = True
        self.plot.add_widget(self)

    def disable(self):
        if not self.enabled:
            return
        self.enabled = False
        self.plot.remove_widget(self)

    def draw(self, *largs):
        self.arrows.clear()
        self.arrows.add(PushMatrix())
        self.arrows.add(Color(*self.arrow_color, mode='rgb'))
        self.arrows.add(self.arrows_translate)

        for x_range in self.x_ranges:
            x_start, x_end = x_range
            assert self.begin_series.data_extents[1] == self.begin_series.data_extents[3] and \
                        self.end_series.data_extents[1] == self.end_series.data_extents[3], "arrows only work with x_only data."
            y_start = self.begin_series.data_extents[1]
            y_end = self.end_series.data_extents[1]

            x1, y1 = [int(v) for v in self.plot.to_display_point(x_start, y_start)]
            x2, y2 = [int(v) for v in self.plot.to_display_point(x_end, y_end)]

            self.arrows.add(Arrow([x1, y1, x2, y2], line_width = 3, head_length = 10))
            print "success"

        self.arrows.add(PopMatrix())

    def _set_pos(self, instance, value):
        print 'setting pos', value
        self.pos = value

    def _set_size(self, instance, value):
        print 'setting size', value
        self.size = value

    def on_pos(self, instance, value):
        self.arrows_translate.xy = self.x, self.y

    def on_size(self, instance, value):
        self.draw()

class Series(Widget):
    fill_color = ListProperty([1,1,1])
    highlight_color = ListProperty([0.949019608,0.941176471,0.741176471, .55])
    col_highlight_color = ListProperty([1,1,1,.55])
    enabled = BooleanProperty(False)
    data = ListProperty([])
    tick_width = NumericProperty(5)
    tick_height = NumericProperty(32)
    marker = StringProperty('tick')
    highlight_regions = ListProperty([])
    col_highlights_distances = ListProperty([None, None])

    def __init__(self, plot, **kwargs):
        kwargs['size_hint'] = (None, None)
        self.plot = plot
        super(Series, self).__init__(**kwargs)
        
        self.highlights = InstructionGroup()
        self.highlights_translate = Translate()
        
        self.col_highlights = InstructionGroup()
        self.col_highlights_translate = Translate()

        self.series = InstructionGroup()
        self.series_translate = Translate()

        self.canvas.add(self.col_highlights)
        self.canvas.add(self.series)
        self.canvas.add(self.highlights)

        self.pos = self.plot.pos
        self.size = self.plot.size
        self.plot.bind(size = self._set_size)
        self.plot.bind(pos = self._set_pos)
        self.plot.bind(viewport = self.draw)


    def enable(self):
        if self.enabled:
            return
        self.enabled = True
        self.plot.add_widget(self)

    def disable(self):
        if not self.enabled:
            return
        self.enabled = False
        self.plot.remove_widget(self)

    def resize_plot_from_data(self):
        self.plot.viewport = self.data_extents
        print self.data_extents
        self.draw()

    def on_data(self, instance, value):
        if value is None or len(value) == 0: return

        self.data_x = zip(*value)[0]
        self.data_y = zip(*value)[1]
        self.data_extents = (min(self.data_x), min(self.data_y), max(self.data_x), max(self.data_y))
        self.draw()

    def on_highlight_regions(self, instance, value):
        print "redrawing with regions", self.highlight_regions
        self.draw()

    def on_col_highlights_distances(self, instance, value):
        print "redrawing with column highlights at", self.col_highlights_distances
        self.draw()

    def draw(self, *largs):
        self.series.clear()
        self.series.add(PushMatrix())
        self.series.add(Color(*self.fill_color, mode='rgb'))
        self.series.add(self.series_translate)

        tick_half_height_px = .5*self.tick_height / self.plot.vp_height_convert

        for t in self.data:
            bar_x = float(t[0])
            if bar_x >= self.plot.viewport[2]: continue
            bar_min_y = t[1] - tick_half_height_px
            bar_max_y = t[1] + tick_half_height_px

            display_pos = [int(v) for v in self.plot.to_display_point(bar_x, bar_min_y)]
            display_size = [int(v) for v in (self.tick_width, self.plot.to_display_point(bar_x, bar_max_y)[1] - display_pos[1])]
            
            if self.marker == 'tick':
                self.series.add(Rectangle(pos = display_pos, size = display_size))
            elif self.marker == 'plus':
                self.series.add(Rectangle(pos = display_pos, size = display_size))
                crossbar_pos = [display_pos[0] - 0.5*(self.tick_height-self.tick_width), display_pos[1] + 0.5*(self.tick_height-self.tick_width)]
                crossbar_size = (self.tick_height, self.tick_width)
                self.series.add(Rectangle(pos = crossbar_pos, size = crossbar_size))

        self.series.add(PopMatrix())

        # now draw the highlights, if there are any
        self.highlights.clear()
        self.highlights.add(PushMatrix())
        self.highlights.add(Color(*self.highlight_color, mode='rgba'))
        self.highlights.add(self.highlights_translate)

        highlight_height = int(1.2 * self.tick_height)

        for highlight_range in self.highlight_regions:
            start, end = highlight_range
            assert self.data_extents[1] == self.data_extents[3], "Highlights only work with x_only data."
            y_center = self.data_extents[1]
            begin_point = [int(v) for v in self.plot.to_display_point(start, y_center)]
            end_point = [int(v) for v in self.plot.to_display_point(end, y_center)]

            self.highlights.add(Rectangle(pos = (begin_point[0], begin_point[1] - highlight_height/2) , size = (end_point[0] - begin_point[0], highlight_height)))

        self.highlights.add(PopMatrix())

        # finally, the col_highlights
        self.col_highlights.clear()
        self.col_highlights.add(PushMatrix())
        # set color to be the same as the series color but at a much lower opacity
        self.col_highlights.add(Color(*(self.fill_color[:3] + [.3]), mode='rgba'))
        self.col_highlights.add(self.col_highlights_translate)

        if None not in self.col_highlights_distances:
            ds = self.col_highlights_distances
            assert self.data_extents[1] == self.data_extents[3], "Highlights only work with x_only data."
            y_start = self.plot.viewport[1]
            y_end = self.plot.viewport[3]

            for t, _ in self.data:
                x_start = t-ds[0]
                x_end = t+ds[1]
                begin_point = [int(v) for v in self.plot.to_display_point(x_start, y_start)]
                end_point = [int(v) for v in self.plot.to_display_point(x_end, y_end)]

                self.col_highlights.add(Rectangle(pos = (begin_point[0], begin_point[1]), size = (end_point[0] - begin_point[0], end_point[1] - begin_point[1])))

        self.col_highlights.add(PopMatrix())



    def _set_pos(self, instance, value):
        print 'setting pos', value
        self.pos = value

    def _set_size(self, instance, value):
        print 'setting size', value
        self.size = value

    def on_pos(self, instance, value):
        self.series_translate.xy = self.x, self.y
        self.highlights_translate.xy = self.x, self.y
        self.col_highlights_translate.xy = self.x, self.y

    def on_size(self, instance, value):
        self.draw()

    def get_legend_icon(self, size=32, **kwargs):
        # returns a kivy Image widget that matches the tick mark used in self.draw, for use in legends etc
        ic = Widget(size_hint = (None, None), size = (size,size))
        with ic.canvas:
            Color(1,1,1, mode='rgb')
            Rectangle(pos=ic.pos, size=ic.size)

class Plot(Widget):
    viewport = ListProperty([0,0,100,10])
    border_width = NumericProperty(5)
    border_color = ListProperty([.3,.3,.3])
    tick_distance_x = NumericProperty(10)
    tick_distance_y = NumericProperty(1)
    tick_color = ListProperty([.3,.3,.3])
    left_margin = NumericProperty(25)
    bottom_margin = NumericProperty(25)
    right_margin = NumericProperty(0)
    top_margin = NumericProperty(0)
    x_axis_title = StringProperty(None) 
    y_axis_title = StringProperty(None)
    text_color = ListProperty([0,0,0])
    x_axis_title_texture = None
    y_axis_title_texture = None

    def __init__(self, **kwargs):
        
        # these can easily be refactored to all use the same translate
        self.ticks = InstructionGroup()
        self.tick_translate = Translate()

        self.border = InstructionGroup()
        self.border_translate = Translate()

        self.x_axis_label = InstructionGroup()
        self.x_axis_label_translate = Translate()

        self.y_axis_label = InstructionGroup()
        self.y_axis_label_translate = Translate()

        
        super(Plot, self).__init__(**kwargs)
        self.canvas.add(self.ticks)
        self.canvas.add(self.border)
        self.canvas.add(self.x_axis_label)
        self.canvas.add(self.y_axis_label)


    # recalculate viewport when size changes
    def on_size(self, instance, value):
        self.on_viewport(None, self.viewport)

    def on_pos(self, instance, value):
        self.tick_translate.xy = self.x, self.y
        self.border_translate.xy = self.x, self.y
        self.x_axis_label_translate.xy = self.x, self.y
        self.y_axis_label_translate.xy = self.x, self.y
        
    def on_viewport(self, instance, value):
        if value is None or len(value) != 4: return
        self.vp_width_convert = (float(self.width)-self.left_margin-self.right_margin)/(value[2] - value[0])
        self.vp_height_convert = (float(self.height)-self.bottom_margin-self.top_margin)/(value[3] - value[1])
        self.draw_ticks()
        self.draw_border()
        self.draw_axis_labels()

    def draw_ticks(self):
        self.ticks.clear()
        self.ticks.add(PushMatrix())
        self.ticks.add(Color(*self.tick_color, mode='rgb'))
        self.ticks.add(self.tick_translate)
        if self.tick_distance_x is not None:
            first_x_tick = self.tick_distance_x*(int(self.viewport[0]/self.tick_distance_x) + 1)
            for x in drange(first_x_tick, self.viewport[2], self.tick_distance_x):
                start = self.to_display_point(x, self.viewport[1])
                stop = self.to_display_point(x, self.viewport[3])
                self.ticks.add(Line(points=[start[0], start[1], stop[0], stop[1]]))

        if self.tick_distance_y is not None:
            first_y_tick = self.tick_distance_y*(int(self.viewport[1]/self.tick_distance_y) + 1)
            for y in drange(first_y_tick, self.viewport[3], self.tick_distance_y):
                start = self.to_display_point(self.viewport[0], y)
                stop = self.to_display_point(self.viewport[2], y)
                self.ticks.add(Line(points=[start[0], start[1], stop[0], stop[1]]))
        
        self.ticks.add(PopMatrix())

    def draw_border(self):
        print "drawing border, pos is", self.pos, "bottom margin is ", self.bottom_margin
        self.border.clear()
        self.border.add(PushMatrix())
        self.border.add(Color(*self.border_color, mode='rgb'))
        self.border.add(self.border_translate)
        if self.border_width != 0:
            self.border.add(Line(rectangle = (self.left_margin, self.bottom_margin, self.width-self.left_margin-self.right_margin, self.height-self.bottom_margin-self.top_margin), width=self.border_width, joint='miter'))
        self.border.add(PopMatrix())

    def draw_axis_labels(self):
        self.x_axis_label.clear()
        self.x_axis_label.add(PushMatrix())
        self.border.add(Color(*self.text_color, mode='rgb'))
        self.x_axis_label.add(self.x_axis_label_translate)
        if self.x_axis_title_texture is not None:
            self.x_axis_label.add(
                        Rectangle(pos = (.5*self.width - .5*self.x_axis_title_texture.size[0], 0), 
                            size = self.x_axis_title_texture.size,
                            texture=self.x_axis_title_texture))
        self.x_axis_label.add(PopMatrix())

        self.y_axis_label.clear()
        self.y_axis_label.add(PushMatrix())
        self.border.add(Color(*self.text_color, mode='rgb'))

        self.y_axis_label.add(self.y_axis_label_translate)

        


        if self.y_axis_title_texture is not None:
            w,h = self.y_axis_title_texture.size

            t = Translate()
            t.xy = (.5*h, .5*self.height)
            self.y_axis_label.add(t)

            rot = Rotate()
            rot.angle = 90
            self.y_axis_label.add(rot)

            self.y_axis_label.add(
                        Rectangle(pos =  (-w*.5, -h*.5),
                            size = (w,h),
                            texture = self.y_axis_title_texture,
                            ))

        
        
        self.y_axis_label.add(PopMatrix())


    def on_y_axis_title(self, instance, value):
        if value is None:
            self.y_axis_title_texture = None
            return
        l = Label(text = value)
        l.texture_update()
        self.y_axis_title_texture = l.texture

    def on_x_axis_title(self, instance, value):
        if value is None: 
            self.x_axis_title_texture = None
            return
        l = Label(text = value)
        l.texture_update()
        self.x_axis_title_texture = l.texture



    def to_display_point(self, x, y):
        return (self.left_margin + self.vp_width_convert*(x-self.viewport[0]), self.bottom_margin + self.vp_height_convert*(y-self.viewport[1]))

class SeriesController(Widget):

    series_dict = {}
    tick_height = 20
    tick_width = 5
    all_variables_list = ListProperty([])
    x_only_fields = []
    arrows = DictProperty({})

    # determines where on the y_axis series show up if they don't have y data
    x_only_field_y_hints = [[],
                            [.75], 
                            [.6, .8], 
                            [.4, .6, .8], 
                            [.2, .4, .6, .8], 
                            [.1, .3, .5, .7, .9],
                            ]

    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.visualizer.bind(viewport = self.viewport_changed)
        self.color_palette = ColorPalette()

    def add_data(self, label, xy_data, marker = 'tick', is_x_only = False):
        if len(xy_data) == 0: return
        # if label is new, make a new series
        if label not in self.series_dict.keys():
            s = Series(self.visualizer, fill_color = self.color_palette.get_color(label), marker = marker, tick_height = self.tick_height, tick_width = self.tick_width)
            self.series_dict[label] = s
            if is_x_only and label not in self.x_only_fields: self.x_only_fields.append(label)
        t = self.series_dict[label]
        if t.data is None: t.data = []
        if is_x_only: 
            t.data = t.data + self.reshape_x_only_data(label, xy_data)
        else:
            t.data = t.data + xy_data
        if label not in self.all_variables_list and len(t.data) > 0: self.all_variables_list.append(label)
        # print self.all_variables_list
        print "Adding %s data points to series '%s'; series now contains %s items." % (len(xy_data), label, len(t.data))

    def reshape_x_only_data(self, label, xy_data):
        enabled_x_only_fields = [l for l in self.x_only_fields if self.series_dict[l].enabled or l == label]
        if len(enabled_x_only_fields) == 0: enabled_x_only_fields = self.x_only_fields
        all_y_hints = self.x_only_field_y_hints[len(enabled_x_only_fields)]
        series_y_hint = all_y_hints[enabled_x_only_fields.index(label)]
        series_y = self.visualizer.viewport[1] + series_y_hint*(self.visualizer.viewport[3] - self.visualizer.viewport[1])
        print [(t[0], series_y) for t in xy_data]
        return [(t[0], series_y) for t in xy_data]


    def viewport_changed(self, instance, value):
        self.reassign_y_values_to_x_only_series()


    def reassign_y_values_to_x_only_series(self):
        for label in self.x_only_fields:
            t = self.series_dict[label]
            if not t.data: continue
            t.data = self.reshape_x_only_data(label, t.data)

    def clear(self, label = None, except_label = None):
        # use clear(label=name) to clear a given column, or use clear(except_label=name) to remove all columns *except* a given column
        if label is not None:
            if label in self.series_dict: self.series_dict[label].data = []
            if label in self.all_variables_list: self.all_variables_list.remove(label)
        elif except_label is not None:
            for each in self.all_variables_list:
                if each != except_label:
                    self.series_dict[each].data = []
            self.all_variables_list = [except_label] if except_label in self.all_variables_list else []

    def update_visible_series(self, list_of_labels):
        for label in self.series_dict.keys():
            if label in list_of_labels:
                self.enable(label)
            else:
                self.disable(label)
        if len(list_of_labels) > 0:
            self.fit_to_all_series()

    def enable(self, label):
        self.series_dict[label].enable()
        if label in self.x_only_fields: self.reassign_y_values_to_x_only_series()

    def disable(self, label):
        self.series_dict[label].disable()
        if label in self.x_only_fields: self.reassign_y_values_to_x_only_series()

    def get_data(self, label):
        return self.series_dict[label].data

    def fit_to_all_series(self):
        all_extents = [None, None, None, None]
        for k, v in self.series_dict.iteritems():
            if v.enabled:
                if all_extents[0] is None or v.data_extents[0] < all_extents[0]:  all_extents[0] = v.data_extents[0]
                if all_extents[1] is None or v.data_extents[1] < all_extents[1]:  all_extents[1] = v.data_extents[1]
                if all_extents[2] is None or v.data_extents[2] > all_extents[2]:  all_extents[2] = v.data_extents[2]
                if all_extents[3] is None or v.data_extents[3] > all_extents[3]:  all_extents[3] = v.data_extents[3]
        if None not in all_extents:
            x_range = all_extents[2] - all_extents[0]
            y_range = all_extents[3] - all_extents[1]
            if x_range <= 0: x_range = 1
            if y_range <= 0: y_range = 1
            self.visualizer.viewport = [all_extents[0] - 0.1*x_range, all_extents[1] - 0.1*y_range,
                                        all_extents[2] + 0.1*x_range, all_extents[3] + 0.1*y_range]

    def add_highlights(self, label, regions):
        self.series_dict[label].highlight_regions = regions

    def add_col_highlights(self, label, before_distance, after_distance):
        self.series_dict[label].col_highlights_distances = (before_distance, after_distance)


    def add_arrows(self, start_label, end_label, x_ranges):
        if (start_label, end_label) not in self.arrows:
            self.arrows[(start_label, end_label)] = ArrowList(self.series_dict[start_label], self.series_dict[end_label], x_ranges)        
        else:
            self.arrows[(start_label, end_label)].x_ranges = x_ranges

        self.arrows[(start_label, end_label)].enable()

    def clear_arrows(self):
        for _, v in self.arrows.iteritems():
            v.disable()

    def clear_highlights(self):
        for _, v in self.series_dict.iteritems():
            v.highlight_regions = []

    def clear_col_highlights(self):
        for _, v in self.series_dict.iteritems():
            v.col_highlights_distances = (None, None)

    def export_bouts(self, label, filename):
        with open(filename, 'w') as outf:
            csvwriter = csv.writer(outf)
            csvwriter.writerow(['Bout ID', 'Start Time', 'End Time', 'Number of Events', 'Avg Inter-event time'])
            data_x = self.series_dict[label].data_x
            for idx, region in enumerate(self.series_dict[label].highlight_regions):
                relevant_data = [x for x in data_x if region[0] <= x <= region[1]]
                inter_event_times = [t[1]-t[0] for t in zip(relevant_data,relevant_data[1:])]
                avg_inter_event_time = sum(inter_event_times)/float(len(inter_event_times)) if len(inter_event_times) > 0 else None
                csvwriter.writerow([idx, region[0], region[1], len(relevant_data), avg_inter_event_time])

    def export_transitions(self, label, filename):
        label1, label2 = [v.strip() for v in label.split('->')]
        with open(filename, 'w') as outf:
            csvwriter = csv.writer(outf)
            csvwriter.writerow(['Transition ID', 'From Event', 'To Event Time', 'First Event Time', 'Second Event Time'])
            for idx, time_range in enumerate(self.arrows[(label1, label2)].x_ranges):
                csvwriter.writerow([idx, label1, label2, time_range[0], time_range[1]])

    def export_events(self, label, filename):
        with open(filename, 'w') as outf:
            csvwriter = csv.writer(outf)
            csvwriter.writerow(['DA transient Peak Time (s)','DA transient Amplitude (nM)',"Matched Event", "Matched Event Time", "Peak time after event"])
            transient_x = self.series_dict['Transients'].data_x
            transient_y = self.series_dict['Transients'].data_y
            event_x = self.series_dict[label].data_x
            before_dist, after_dist = self.series_dict[label].col_highlights_distances

            for peak_time, amplitude in zip(transient_x, transient_y):
                related_events = [x for x in event_x if x-abs(before_dist) <= peak_time <= x+abs(after_dist)]
                if len(related_events) == 0:
                    event_label = None
                    matched_event = None
                    time_diff = None
                else:
                    event_label = label
                    matched_event = min(related_events, key = lambda k: abs(peak_time-k))
                    time_diff = peak_time - matched_event

                csvwriter.writerow([peak_time, amplitude, event_label, matched_event, time_diff])


class ColorPalette(object):
    colors = [
    (0., 0.274509804, 0.784313725),
    (0.949019608, 0.596078431, 0.),
    (0.784313725, 0., 0.),
    (0.305882353, 0., 0.619607843),
    (0.968627451, 0.811764706, 0.)
    ]

    color_dict = {}
    next_color_up = 0

    def _get_and_assign_color(self, label):
        c = self.colors[self.next_color_up]
        self.next_color_up = (self.next_color_up + 1) % len(self.colors)
        self.color_dict[label] = c
        return c

    def get_color(self, label):
        try:
            return self.color_dict[label]
        except KeyError:
            return self._get_and_assign_color(label)


class PlotExplorer(Widget):
    plot_container = ObjectProperty(None)
    annotations = ListProperty([])

    def __init__(self, plot_widget, annotations_dict, **kwargs):
        super(PlotExplorer, self).__init__(**kwargs)
        self.plot_widget = plot_widget
        self.annotations_dict = annotations_dict
        self.plot_container.add_widget(self.plot_widget)
        self.plot_container.bind(pos=self._reposition_plot)

    def on_touch_down(self, touch):
        if self.plot_widget.collide_point(*touch.pos):
            self.display_annotation(self.plot_widget.select_point(*touch.pos))

    def on_touch_move(self, touch):
        if self.plot_widget.collide_point(*touch.pos):
            self.display_annotation(self.plot_widget.select_point(*touch.pos))

    def _reposition_plot(self, instance, pos):
        self.plot_widget.pos = pos

    def display_annotation(self, data_point):
        try:
            self.annotations = self.annotations_dict[data_point[0]]
        except KeyError:
            self.annotations = []
