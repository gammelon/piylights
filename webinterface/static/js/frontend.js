angular.module('plWeb', ["ngResource", "plWeb.controllers", "plWeb.services"]);
angular.module("plWeb").config(['$interpolateProvider', function($interpolateProvider) {
	$interpolateProvider.startSymbol('{a');
	$interpolateProvider.endSymbol('a}');
}]);

angular.module("plWeb.services",[]).factory("Parameter", function($resource) {
	return $resource("/api/parameters/:name",
		{name: "@_id"},
		{query: {method:"GET", isArray:false}},
		{update: {method: "PUT"}});
});

angular.module("plWeb.controllers", []);
angular.module("plWeb.controllers").controller('ParameterController', function($scope, Parameter) {
	$scope.parameters = Parameter.query();

});
