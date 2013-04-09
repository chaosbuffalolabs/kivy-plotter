from kivy.app import App
from plot import Plot, SeriesController
from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty
import csv


Builder.load_string("""
<MainView>:
    plot: plot
    BoxLayout:
        pos: root.pos
        size: root.size
        orientation: 'vertical'
        spacing: 10
        padding: 10
        Plot:
            id: plot
            size_hint: (1, .8)
            viewport: [0,0,30,30]
            tick_distance_x: 2
            tick_distance_y: 5
        BoxLayout:
            size_hint: (1, .2)
            orientation: 'horizontal'
            spacing: 10
            ToggleButton: 
                text: "Series 1"
                on_release: root.add_button_pressed(self.state)
            ToggleButton:
                text: "Series 2"
                on_release: root.add_button_2_pressed(self.state)


    """)

def get_data_from_csv(csvfile, has_header=True):
    with open(csvfile, 'r') as inf:
        reader = csv.reader(inf)
        for idx, line in enumerate(reader):
            if idx == 0 and has_header: continue
            yield (float(line[0]), float(line[1]))



class MainView(Widget):
    plot = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(MainView, self).__init__(**kwargs)
        self.series_controller = SeriesController(self.plot)

    def add_button_pressed(self, state):
        if state == 'down':
            try:
                self.series_controller.enable('Series 1')
            except KeyError:
                xy_data = [t for t in get_data_from_csv('sample_data_1.csv')]
                self.series_controller.add_data('Series 1', xy_data, marker='plus')
                self.series_controller.enable('Series 1')
        else:
            self.series_controller.disable('Series 1')

        self.series_controller.fit_to_all_series()

    def add_button_2_pressed(self, state):
        if state == 'down':
            try:
                self.series_controller.enable('Series 2')
            except KeyError:
                xy_data = [t for t in get_data_from_csv('sample_data_2.csv')]
                self.series_controller.add_data('Series 2', xy_data, marker='tick')
                self.series_controller.enable('Series 2')
        else:
            self.series_controller.disable('Series 2')
            
        self.series_controller.fit_to_all_series()

class PlotDemo(App):
    def build(self):
        return MainView()


if __name__ == '__main__':
    PlotDemo().run()
