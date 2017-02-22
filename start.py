#!flask/bin/python
import os, sys, inspect
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"webinterface")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

from webinterface import app
app.run(debug=True, use_reloader=False, host="0.0.0.0")
