var dashboard = angular.module('dashboard',[]);

dashboard.controller('dashboardCtrl', ['$scope', '$http', function($scope, $http) {
  	$http.get('/static/results_30day.json').then(function(results) {  		
  		$scope.pageviews30day = results.data.rows;
  		$scope.pageviewsTotal30day = results.data.totalsForAllResults['ga:pageviews'];  			
  	});

  	$http.get('/static/results_7day.json').then(function(results) {
  		$scope.pageviews7day = results.data.rows;
  		$scope.pageviewsTotal7day = results.data.totalsForAllResults['ga:pageviews'];
  	});

  	$http.get('/static/results_1day.json').then(function(results) {
  		$scope.pageviews1day = results.data.rows;
  		$scope.pageviewsTotal1day = results.data.totalsForAllResults['ga:pageviews'];
  	});
}]);