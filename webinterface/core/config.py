from parser import Parser
import json
import os.path

class Config:

    def __init__(self, path):
        self.path = path
        self.presets = {}
        if not os.path.isfile(path):
            with open(path, "w") as f:
                json.dump(self.presets, f)

        self._loadFromFile()

    def _loadFromFile(self):
        with open(self.path, "r") as f:
            self.presets = json.load(f)

    def _saveToFile(self):
        with open(self.path, "w") as f:
            json.dump(self.presets, f)

    def loadPreset(self, preset, parameters):
        return self._populateParam(parameters, self.presets[preset])

    def deletePreset(self, preset):
        del self.presets[preset]

    def storeCurrentAndWrite(self, parameters):
        print("saving config")
        self.storePreset("+", parameters)
        self._saveToFile()

    def storePreset(self, preset, parameters):
        if type(parameters["active"]) == type({}):
            self.presets[preset] = self._shrinkParam(parameters)
        else:
            self.presets[preset] = parameters

    def _shrinkParam(self, parameters):
        shrink = {}
        for key in parameters.keys():
            shrink[key] = parameters[key]["value"]
        return shrink

    def _populateParam(self, parameters, shrinked):
        for key in parameters.keys():
            parameters[key]["value"] = shrinked[key]
        return parameters
