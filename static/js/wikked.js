/**
 * RequireJS configuration.
 *
 * We need to alias/shim some of the libraries.
 */
require.config({
    urlArgs: "bust=" + (new Date()).getTime(),
    paths: {
        jquery: 'js/jquery-1.8.3.min',
        underscore: 'js/underscore-min',
        backbone: 'js/backbone-min',
        handlebars: 'js/handlebars-1.0.rc.1',
        moment: 'js/moment.min',
        text: 'js/text',
        bootstrap_modal: '/bootstrap/js/bootstrap-modal'
    },
    shim: {
        'jquery': {
            exports: '$'
        },
        'underscore': {
            exports: '_'
        },
        'backbone': {
            deps: ['underscore', 'jquery'],
            exports: 'Backbone'
        },
        'handlebars': {
            exports: 'Handlebars'
        },
        'bootstrap_modal': {
            deps: ['jquery']
        }
    }
});

//-------------------------------------------------------------//

/**
 * Entry point: run Backbone!
 *
 * We also import scripts like `handlebars` that are not used directly
 * by anybody, but need to be evaluated.
 */
require([
        'js/wikked/app',
        'js/wikked/handlebars',
        'backbone',
        'text'
        ],
    function(app, hb, Backbone, textExtension) {

    var router = new app.Router();
    Backbone.history.start();//{ pushState: true });

});

