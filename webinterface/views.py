from flask import render_template, jsonify, request, abort
from webinterface import app # varialbe containing instance of flask app
from webinterface import piylights # variable containing instance of Piylights
from core.parser import Parser

@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html", title="piylights webinterface", parameters=piylights.parameters)

@app.route("/api/parameters", methods=["GET"])
def getAllParameters():
    return jsonify({"result" : {"parameters" : piylights.parameters}, "status" : "SUCCESS"})

@app.route("/api/parameters/<string:parameterName>", methods=["GET"])
def getParameter(parameterName):
    if parameterName in piylights.parameters:
        return jsonify({"result" : piylights.parameters[parameterName], "status" : "SUCCESS"})
    else:
        return jsonify({"result" : "", "status" : "FAILURE", "error" : "parameter " + str(parameterName) + " not present in configuration"})

@app.route("/api/parameters/<string:parameterName>", methods=["POST"])
def setParameter(parameterName):
    if parameterName not in piylights.parameters:
        return jsonify({"result" : "", "status" : "FAILURE", "error" : "parameter " + str(parameter) + " not present in configuration"})
    else:
        if not request.json:
            abort(400)
        if not "value" in request.json:
            abort(400)
        if piylights.setParam(parameterName, request.json["value"]):
            return jsonify({"result" : "", "status" : "SUCCESS"})
        else:
            return jsonify({"result" : "", "status" : "FAILURE"})

@app.route("/api/presets", methods=["GET"])
def getAllPresets():
    return jsonify({"result" : {"presets" : piylights.getPresets()}, "status" : "SUCCESS"})

@app.route("/api/presets/<string:presetName>", methods=["GET"])
def getPreset(presetName):
    if presetName in piylights.getPresets():
        return jsonify({"result" : piylights.getPresets()[presetName], "status" : "SUCCESS"})
    else:
        return jsonify({"result" : "", "status" : "FAILURE", "error" : "no preset named " + str(presetName) + " in configuration"})

@app.route("/api/presets/<string:presetName>", methods=["POST"])
def setPreset(presetName):
    if not request.json:
        abort(400)
    piylights.storePreset(presetName, request.json)
    return jsonify({"result" : "", "status" : "SUCCESS"})

@app.route("/api/presets/<string:presetName>", methods=["DELETE"])
def deletePreset(presetName):
    if presetName not in piylights.getPresets():
        return jsonify({"result" : "", "status" : "FAILURE", "error" : "no preset named " + str(presetName) + " in configuration"})
    else:
        piylights.deletePreset(presetName)
        return jsonify({"result" : "", "status" : "SUCCESS"})
