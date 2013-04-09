from kivy_plotter.plot import Series, ArrowList
from kivy.properties import ListProperty, DictProperty
from kivy.uix.widget import Widget
from copy import copy
import csv


class Workspace(object):
    """This class contains all the information required to load or save a workspace"""

    transient_files = []
    behavior_files = []
    selected_transient_filenames = []
    selected_behavior_filenames = []
    schema = None

    selected_bout_variables = []
    bout_threshold = 1.

    all_transition_variable_pairs = []
    selected_transition_variable_pairs = []
    transition_threshold = 1.

    selected_event_matching_variables = []
    event_matching_before_threshold = -2
    event_matching_after_threshold = 2

    visible_series = []

    def save(self, mainview_widget):
        m = mainview_widget
        
        self.transient_files = copy(m.transient_files)
        self.selected_transient_filenames = [v.text for v in m.transient_button_list.current_toggled]

        self.behavior_files = copy(m.behavior_files)
        self.selected_behavior_filenames = [v.text for v in m.behavior_button_list.current_toggled]
        self.schema = m.schema

        self.selected_bout_variables = [v.text for v in m.bout_id_button_list.current_toggled]
        self.bout_threshold = m.bout_id_box.bout_threshold

        self.all_transition_variable_pairs = list(m.transition_button_list.variable_list)
        self.selected_transition_variable_pairs = [v.text for v in m.transition_button_list.current_toggled]
        self.transition_threshold = m.transition_box.transition_threshold

        self.selected_event_matching_variables = [v.text for v in m.event_button_list.current_toggled]
        self.event_matching_before_threshold = m.event_box.before_threshold
        self.event_matching_after_threshold = m.event_box.after_threshold

        self.visible_series = [v.text for v in m.legend_button_list.current_toggled]

    def load(self, mainview_widget):
        m = mainview_widget

        print "setting transient files to ", self.transient_files
        m.transient_files = self.transient_files
        m.transient_button_list.deselect_all()
        for f in self.selected_transient_filenames:
            m.transient_button_list.set_state(f, 'down')

        m.schema = self.schema
        m.behavior_files = self.behavior_files
        m.behavior_button_list.deselect_all()
        for f in self.selected_behavior_filenames:
            m.behavior_button_list.set_state(f, 'down')

        # this might need to be scheduled for after the previous section gets completed.
        # it doesn't seem like it now, but we ought to test on a slower computer. Not sure
        # if Kivy property watching is instant or waits a frame. I think it's instant.
        
        m.bout_id_button_list.deselect_all()
        for f in self.selected_bout_variables:
            m.bout_id_button_list.set_state(f, 'down')
        m.bout_id_box.slider.value = self.bout_threshold

        m.transition_button_list.variable_list =  self.all_transition_variable_pairs
        m.transition_button_list.deselect_all()
        for f in self.selected_transition_variable_pairs:
            m.transition_button_list.set_state(f, 'down')
        m.transition_box.slider.value = self.transition_threshold

        m.event_button_list.deselect_all()
        for f in self.selected_event_matching_variables:
            m.event_button_list.set_state(f, 'down')
        m.event_box.ds.value = self.event_matching_before_threshold
        m.event_box.ds.value2 = self.event_matching_after_threshold

        m.legend_button_list.deselect_all()
        for f in self.visible_series:
            m.legend_button_list.set_state(f, 'down')

class Subject(object):
    def __init__(self, name):
        self.name = name
        self.workspace = Workspace()

    def __str__(self):
        return self.name

class Session(object):

    def __init__(self, name):
        self.name = name
        self.subjects = []

    def add_subject(self, subject_name):
        self.subjects.append(Subject(subject_name))

    def remove_subject(self, subject):
        print self.subjects
        self.subjects.remove(subject)
        print self.subjects

    def __str__(self):
        return self.name

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

    def get_and_assign_color(self, label):
        c = self.colors[self.next_color_up]
        self.next_color_up = (self.next_color_up + 1) % len(self.colors)
        self.color_dict[label] = c
        return c

    def get_color(self, label):
        try:
            return self.color_dict[label]
        except KeyError:
            return self.get_and_assign_color(label)
