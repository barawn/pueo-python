import numpy as np
import telemevent as te
import trigger
import ipywidgets as widgets
from io import BytesIO
import matplotlib.pyplot as plt

def surf_subplot(ymin, ymax):
    # we want to create a 4 row, 2 column plot, with only
    # yticks on the left, and xticks on the bottom.
    # margin out 0.05 on both sides, so we have 0.9 wide
    # and 0.9 high. 0.225 height and 0.45 width.
    fig = plt.figure()
    ax = []
    for i in range(4):
        if i != 3:
            ax.append(fig.add_axes([0.05, 0.05+(3-i)*0.225, 0.45, 0.225],
                      xticklabels=[], ylim=(ymin, ymax)))
        else:
            ax.append(fig.add_axes([0.05, 0.05+(3-i)*0.225, 0.45, 0.225],
                      ylim=(ymin, ymax)))
    for i in range(4):
        if i != 3:
            ax.append(fig.add_axes([0.50, 0.05+(3-i)*0.225, 0.45, 0.225],
                      yticklabels=[],xticklabels=[], ylim=(ymin, ymax)))
        else:
            ax.append(fig.add_axes([0.50, 0.05+(3-i)*0.225, 0.45, 0.225],
                      yticklabels=[],ylim=(ymin, ymax)))
    return ax

def draw_surf(the_surf):
    maxes = []
    mins = []
    for i in range(8):
        maxes.append(max(the_surf[i]))
        mins.append(min(the_surf[i]))
    global_max = max(maxes)
    global_min = min(mins)
    ax = surf_subplot(global_min, global_max)
    cmap = [0,1,2,3,4,5,6,7]
    for i in range(8):
        ax[i].plot(the_surf[cmap[i]])
    plt.show()


def on_upload_change(change):
    me = change['owner']
    ed = me.the_display
    ed.file_name_label.value = ed.file_uploader.value[0].name
    uploaded_file = ed.file_uploader.value[0]
    ed.the_file = te.TelemFile(BytesIO(uploaded_file.content))
    ed.event_selector.options = ed.the_file.events.keys()
    ed.event_selector.value = ed.event_selector.options[0]

def on_event_change(change):
    me = change['owner']
    ed = me.the_display
    e = ed.the_file.events[ed.event_selector.value]
    ed.the_event = e

    ed.event_info.value = repr(ed.the_event)
    vdaq_surfs = sorted(e.vdaq.keys())
    hdaq_surfs = sorted(e.hdaq.keys())
    lf_surfs = sorted(e.lf.keys())

    ed.vdaq_selector.the_surf = None
    ed.hdaq_selector.the_surf = None
    ed.lf_selector.the_surf = None
    
    if len(vdaq_surfs):
        ed.vdaq_selector.options = vdaq_surfs
        ed.vdaq_selector.disabled = False
    else:
        ed.vdaq_selector.options = []
        ed.vdaq_selector.disabled = True
    if len(hdaq_surfs):
        ed.hdaq_selector.options = hdaq_surfs
        ed.hdaq_selector.disabled = False
    else:
        ed.hdaq_selector.options = []
        ed.hdaq_selector.disabled = True
    if len(lf_surfs):
        ed.lf_selector.options = lf_surfs
        ed.lf_selector.disabled = False
    else:
        ed.lf_selector.options = []
        ed.lf_selector.disabled = True

def on_surf_change(change):
    me = change['owner']
    ed = me.the_display
    new_surf = change['new']
    me.the_surf = ed.the_event.__dict__[me.daq_type][new_surf]
    me.outbox.clear_output()
    with me.outbox:
        draw_surf(me.the_surf)

class EventDisplay:
    def __init__(self):
        self.the_file = None
        self.the_event = None
        
        self.file_name_label = widgets.Label("")
        # file uploader needs a trigger, so it needs to recurse
        self.file_uploader = widgets.FileUpload()
        self.file_uploader.the_display = self
        # event selector needs a trigger, so it needs to recurse
        self.event_selector = widgets.Dropdown(description='Event')
        self.event_selector.the_display = self

        self.file_box = widgets.HBox([self.file_uploader, self.file_name_label, self.event_selector])

        self.event_tab = widgets.Tab()
        self.vdaq_selector = widgets.Dropdown(description='SURF',disabled=True)
        self.vdaq_selector.the_display = self
        self.vdaq_selector.daq_type = 'vdaq'
        self.vdaq_output = widgets.Output()
        self.vdaq_selector.outbox = self.vdaq_output
        self.vdaq_box = widgets.VBox([self.vdaq_selector, self.vdaq_output])

        self.hdaq_selector = widgets.Dropdown(description='SURF',disabled=True)
        self.hdaq_selector.the_display = self
        self.hdaq_selector.daq_type = 'hdaq'
        self.hdaq_output = widgets.Output()
        self.hdaq_selector.outbox = self.hdaq_output
        self.hdaq_box = widgets.VBox([self.hdaq_selector, self.hdaq_output])

        self.lf_selector = widgets.Dropdown(description='SURF',disabled=True)
        self.lf_selector.the_display = self
        self.lf_selector.daq_type = 'lf'
        self.lf_output = widgets.Output()
        self.lf_selector.outbox = self.lf_output
        self.lf_box = widgets.VBox([self.lf_selector, self.lf_output])

        self.event_info = widgets.Label()
        self.event_tab.children = [self.vdaq_box, self.hdaq_box, self.lf_box]
        self.event_tab.titles = ['VDAQ', 'HDAQ', 'LF']

        self.event_box = widgets.VBox([self.event_info, self.event_tab])

        self.layout = widgets.VBox([self.file_box, self.event_box])

        self.file_uploader.observe(on_upload_change, names='value')
        self.event_selector.observe(on_event_change, names='value')
        self.vdaq_selector.observe(on_surf_change, names='value')
        self.hdaq_selector.observe(on_surf_change, names='value')
        self.lf_selector.observe(on_surf_change, names='value')

    def run(self):
        display(self.layout)
