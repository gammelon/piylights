import os, sys, inspect
import signal
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"core")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

from flask import Flask
app = Flask(__name__)

from core.server import Piylights
piylights = Piylights()

from webinterface import views

def signal_handler(signal, frame):
    print("shutdown requested")
    piylights.shutdown()

signal.signal(signal.SIGINT, signal_handler)
