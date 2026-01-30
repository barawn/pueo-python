# Simple Event Display

These guys are designed to run in a Jupyter notebook. You can literally
do it on jupyter.org's Try Jupyter site.

Just upload these files, create a notebook, and do

```
from display import EventDisplay
ed = EventDisplay()
ed.run()
```

You can then upload either ".wf" or ".wfs" files (I think!). You can
concatenate them together as well, it doesn't matter, it'll parse
them all.

Note that after you select an event, you can actually muck around
with the data inside the Jupyter notebook. e.g., go and select
an event, and then on the subsequent entry lines:

```
[2]: e = ed.the_event
     print(e)
[2]: Run: 1309 Event: 48575
     Second: 1767858466 Subsecond: 0.365561888
     Priority: 0x8022 Trigger Info: 0x20000
```

If you go back and change to a different event, the next Jupyter
lines will reference that new event too.