import numpy as np
import telemevent as te
import trigger
import ipywidgets as widgets
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.tri as tri
from functools import partial

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

def draw_surf(the_surf, the_display, label, mode='time'):
    run, event, daq, surfno = label.split('.')
    surfno = int(surfno)    
    # Channel ordering in the plots. Currently pointless but maybe
    # useful at some point.
    cmap = [0,1,2,3,4,5,6,7]
    if mode == 'time':
        maxes = []
        mins = []
        for i in range(8):
            if i in the_surf:
                maxes.append(max(the_surf[i]))
                mins.append(min(the_surf[i]))
        global_max = max(maxes)
        global_min = min(mins)
        ax = surf_subplot(global_min, global_max)
        for i in range(8):
            if i == 0:
                ax[i].set_title(f'{daq} Phi Sector {surfno*2}')
            if i == 4:
                ax[i].set_title(f'{daq} Phi Sector {surfno*2+1}')
            if cmap[i] in the_surf:
                ax[i].plot(the_surf[cmap[i]])
    elif mode == 'freq':
        cacheval = f'{label}fft'
        # look for cached FFTs
        if cacheval not in the_display.cache:
            ffts = {}
            for i in range(8):
                if i in the_surf:
                    ffts[i] = np.fft.rfft(the_surf[i])
            the_display.cache[cacheval] = ffts
        freq = np.fft.rfftfreq(1024, d=(1/3000.))
        ax = surf_subplot(100, 200)
        for i in range(8):
            if cmap[i] in the_display.cache[cacheval]:
                ax[i].plot(freq, 20*np.log(np.abs(the_display.cache[cacheval][cmap[i]])))
    elif mode == 'beam':
        # ah, beam mode.
        cacheval = f'{label}beams'
        if cacheval not in the_display.cache:
            d = []
            for i in range(8):
                d.append(the_surf[i])
            b = trigger.beamify(d)
            the_display.cache[cacheval] = b
        envelopes = trigger.envelope(the_display.cache[cacheval])
        maxes = []
        for i in range(48):
            maxes.append(np.max(envelopes[i]))            
        max_beam = np.argmax(maxes)
        fig, (ax1, ax2) = plt.subplots(nrows=2)
        ax1.tricontour(trigger.BEAM_AZIMUTH, trigger.BEAM_ELEVATION, maxes, cmap='Reds')
        ax1.set_title(f'Beam envelope maxima')
        ax2.plot(the_display.cache[cacheval][max_beam])
        ax2.set_title(f'Beam {max_beam} trigger view')
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
    ed.cache = {}
    
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

def on_surf_change(change, daqtype):
    me = change['owner']
    mode = me.mode.value
    ed = me.the_display
    new_surf = change['new']
    me.the_surf = ed.the_event.__dict__[me.daq_type][new_surf]
    # create a label for the cache, like 1504.3303.vdaq.7
    label = f'{ed.the_event.run}.{ed.the_event.event}.{daqtype}.{new_surf}'
    me.outbox.clear_output()
    with me.outbox:
        draw_surf(me.the_surf, ed, label, mode)

def on_mode_change(change, daqtype):
    me = change['owner']
    sel = me.selector
    ed = sel.the_display
    new_mode = change['new']
    old_mode = change['old']
    if new_mode != old_mode:
        sel.outbox.clear_output()
        label = f'{ed.the_event.run}.{ed.the_event.event}.{daqtype}.{sel.value}'
        with sel.outbox:
            draw_surf(sel.the_surf, ed, label, new_mode)

class EventDisplay:
    def __init__(self):
        self.the_file = None
        self.the_event = None
        self.cache = {}
        
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
        self.vdaq_mode = widgets.Dropdown(description='View Mode',
                                          options=['time', 'freq', 'beam'])        
        self.vdaq_selbox = widgets.HBox([self.vdaq_selector, self.vdaq_mode])
        self.vdaq_selector.the_display = self
        self.vdaq_selector.mode = self.vdaq_mode
        self.vdaq_selector.daq_type = 'vdaq'
        self.vdaq_output = widgets.Output()
        self.vdaq_selector.outbox = self.vdaq_output
        self.vdaq_mode.selector = self.vdaq_selector
        self.vdaq_box = widgets.VBox([self.vdaq_selbox, self.vdaq_output])

        self.hdaq_selector = widgets.Dropdown(description='SURF',disabled=True)
        self.hdaq_mode = widgets.Dropdown(description='View Mode',
                                          options=['time', 'freq', 'beam'])        
        self.hdaq_selbox = widgets.HBox([self.hdaq_selector, self.hdaq_mode])
        self.hdaq_selector.the_display = self
        self.hdaq_selector.mode = self.hdaq_mode
        self.hdaq_selector.daq_type = 'hdaq'
        self.hdaq_output = widgets.Output()
        self.hdaq_selector.outbox = self.hdaq_output
        self.hdaq_mode.selector = self.hdaq_selector
        self.hdaq_box = widgets.VBox([self.hdaq_selbox, self.hdaq_output])

        self.lf_selector = widgets.Dropdown(description='SURF',disabled=True)
        self.lf_mode = widgets.Dropdown(description='View Mode',
                                          options=['time', 'freq', 'beam'])        
        self.lf_selbox = widgets.HBox([self.lf_selector, self.lf_mode])
        self.lf_selector.the_display = self
        self.lf_selector.mode = self.lf_mode
        self.lf_selector.daq_type = 'lf'
        self.lf_output = widgets.Output()
        self.lf_selector.outbox = self.lf_output
        self.lf_mode.selector = self.lf_selector
        self.lf_box = widgets.VBox([self.lf_selbox, self.lf_output])

        self.event_info = widgets.Label()
        self.event_tab.children = [self.vdaq_box, self.hdaq_box, self.lf_box]
        self.event_tab.titles = ['VDAQ', 'HDAQ', 'LF']

        self.event_box = widgets.VBox([self.event_info, self.event_tab])

        self.layout = widgets.VBox([self.file_box, self.event_box])

        self.file_uploader.observe(on_upload_change, names='value')
        self.event_selector.observe(on_event_change, names='value')
        self.vdaq_selector.observe(partial(on_surf_change, daqtype='vdaq'), names='value')
        self.vdaq_mode.observe(partial(on_mode_change, daqtype='vdaq'), names='value')
        self.hdaq_selector.observe(partial(on_surf_change, daqtype='hdaq'), names='value')
        self.hdaq_mode.observe(partial(on_mode_change, daqtype='hdaq'), names='value')
        self.lf_selector.observe(partial(on_surf_change, daqtype='lf'), names='value')
        self.lf_mode.observe(partial(on_mode_change, daqtype='lf'), names='value')

    def run(self):
        display(self.layout)
