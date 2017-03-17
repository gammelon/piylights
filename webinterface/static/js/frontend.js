var plWebv = angular.module('plWeb', ["ngResource", "plWeb.controller", "plWeb.services"]);
plWebv.config(['$interpolateProvider', function($interpolateProvider) {
        $interpolateProvider.startSymbol('{a');
        $interpolateProvider.endSymbol('a}');
}]);

plWebv.run(function($rootScope) {
        ['isArray', 'isDate', 'isDefined', 'isFunction', 'isNumber', 'isObject', 'isString', 'isUndefined'].forEach(function(name) {
                $rootScope[name] = angular[name];
        });
});

plWebv.run(function($rootScope) {
        $rootScope.typeOf = function(value) {
                return typeof value;
        };
});
var plWebservicesv = angular.module("plWeb.services",[]);
plWebservicesv.factory("Parameter", function($resource) {
        return $resource("/api/parameters/:parameterName", {parameterName: "@parameterName"},
                {query: {method:"GET", isArray:false}})
});

plWebservicesv.factory("Preset", function($resource) {
        return $resource("/api/presets/:presetName", {presetName: "@presetName"},
                {query: {method:"GET", isArray:false}},
                {delete: {method: "DELETE"}});
});
plWebservicesv.factory("Method", function($resource) {
        return $resource("/api/methods/:methodName", {},
                {query: {method:"GET", isArray:false}},
                );
});

var plWebcontrollersv = angular.module("plWeb.controller", ["plWeb.services"]);
plWebcontrollersv.controller('plWebCtrl', function($scope, Parameter, Preset, Method) {
    $scope.parameters = Parameter.query();
    $scope.chain = [0];

    $scope.presets = Preset.query();
    $scope.methods = Method.query();

    $scope.togglePiylights = function(b) {
        Parameter.save({parameterName:"active"},{value: b});
        $scope.parameters.result.parameters["active"]["value"] = b;
    }

    $scope.saveParameter = function(parametername) {
        saveParameterNoQuery(parametername);
        $scope.parameters = Parameter.query();
    }

    saveParameterNoQuery = function(parametername) {
        Parameter.save({parameterName: parametername},{value:$scope.parameters.result.parameters[parametername]["value"]});
    }

    $scope.saveAll = function() {
        for (var key in $scope.parameters.result.parameters) {
            saveParameterNoQuery(key);
        }
    }

    $scope.deletePreset = function(presetname) {
        Preset.delete({presetName:presetname});
        $scope.presets = Preset.query();
    }

    $scope.storePreset = function(presetname) {
        var dic = {};
        for (var key in $scope.parameters.result.parameters) {
            dic[key] = $scope.parameters.result.parameters[key]["value"];
        }
        Preset.save({presetName:presetname}, dic);
        $scope.presets = Preset.query();
    }

    $scope.loadPreset = function(presetName) {
        for (var key in $scope.parameters.result.parameters) {
            $scope.parameters.result.parameters[key]["value"] = $scope.presets.result.presets[presetName][key];
        }
        $scope.PresetName = presetName;
        $scope.saveAll();
    }

    $scope.hasPresets = function() {
        if (typeof($scope.presets.result) == "undefined"){
            return false;
        }
        return (Object.keys($scope.presets.result.presets).length > 1);
    }

    $scope.countPresets = function() {
        if (typeof($scope.presets.result) == "undefined"){
            return 0;
        }
        return Object.keys($scope.presets.result.presets).length - 1;
    }

    $scope.appendChain = function() {
        var i = $scope.parameters.result.parameters.chain.value.chain.length;
        $scope.insertChain(i);
    }

    $scope.deleteChain = function(i) {
        $scope.parameters.result.parameters.chain.value.chain.splice(i,1);
    }

    $scope.insertChain = function(i) {
        $scope.parameters.result.parameters.chain.value.chain.splice(i, 0, [100,"do_nothing",{}]);
    }

    $scope.saveChain = function() {
        Parameter.save({parameterName:"chain"}, $scope.parameters.result.parameters.ch);
        $scope.parameters = Parameter.query();
    }

    $scope.changeChain = function(i) {
        for (var key in $scope.methods[$scope.parameters.result.parameters.chain.value.chain[i][1]].params) {
            $scope.parameters.result.parameters.chain.value.chain[i][2][key] = $scope.methods[$scope.parameters.result.parameters.chain.value.chain[i][1]].params[key]["default"];
        }
    }

});
