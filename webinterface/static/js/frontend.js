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

var plWebcontrollersv = angular.module("plWeb.controller", ["plWeb.services"]);
plWebcontrollersv.controller('plWebCtrl', function($scope, Parameter, Preset) {
        $scope.parameters = Parameter.query();
    
        $scope.presets = Preset.query();

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
            $scope.saveAll();
        }

        $scope.hasPresets = function() {
            if (typeof($scope.presets.result) == "undefined"){
                return false;
            }
            return (Object.keys($scope.presets.result.presets).length > 1);
        }

});

plWebcontrollersv.controller('MainCtrl', function() {
});
