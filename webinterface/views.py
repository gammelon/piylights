from flask import render_template, jsonify
from webinterface import app # varialbe containing instance of flask app
from webinterface import piylights # variable containing instance of Piylights
from core.parser import Parser

@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html", title="piylights webinterface", parameters=piylights.parameters)

@app.route("/getallparameters", methods=["GET"])
def getallparameters():
    return jsonify({"result" : {"parameters" : piylights.parameters}, "status" : "SUCCESS"})

@app.route("/getalllimits", methods=["GET"])
def getalllimits():
    return jsonify({"result" : {"limits" : piylights.limits}, "status" : "SUCCESS"} )

@app.route("/getparameter/<string:parameter>", methods=["GET"])
def getparameter(parameter):
    if parameter in piylights.parameters:
        return jsonify({"result" : piylights.parameters[parameter], "status" : "SUCCESS"})
    else:
        return jsonify({"result" : "", "status" : "FAILURE", "error" : "parameter " + str(parameter) + " not present in configuration"})

@app.route("/getlimit/<string:parameter>", methods=["GET"])
def getlimit(parameter):
    if parameter in piylights.limits:
        return jsonify({"result" : piylights.limits[parameter], "status" : "SUCCESS"})
    else:
        return jsonify({"result" : "", "status" : "FAILURE", "error" : "parameter " + str(parameter) + " not present in limit db"})

@app.route("/setparameter/<string:parameter>/<string:value>", methods=["GET"])
def setparameter(parameter, value):
    if parameter not in piylights.parameters:
        return jsonify({"result" : "", "status" : "FAILURE", "error" : "parameter " + str(parameter) + " not present in configuration"})
    else:
        if piylights.setParam(parameter, Parser.parse_single(value)):
            return jsonify({"result" : "", "status" : "SUCCESS"})
        else:
            return jsonify({"result" : "", "status" : "FAILURE"})
