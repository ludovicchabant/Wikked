/**
 * RequireJS configuration.
 *
 * We need to alias/shim some of the libraries.
 */
require.config({
    urlArgs: "bust=" + (new Date()).getTime(),
    paths: {
        jquery: 'js/jquery-1.8.3.min',
        jquery_validate: 'js/jquery/jquery.validate.min',
        underscore: 'js/underscore-min',
        backbone: 'js/backbone-min',
        handlebars: 'js/handlebars-1.0.rc.1',
        moment: 'js/moment.min',
        text: 'js/text',
        bootstrap_modal: 'bootstrap/js/modal',
        bootstrap_tooltip: 'bootstrap/js/tooltip',
        bootstrap_alert: 'bootstrap/js/alert',
        bootstrap_collapse: 'bootstrap/js/collapse',
        pagedown_converter: 'js/pagedown/Markdown.Converter',
        pagedown_editor: 'js/pagedown/Markdown.Editor',
        pagedown_sanitizer: 'js/pagedown/Markdown.Sanitizer'
    },
    shim: {
        'jquery': {
            exports: '$'
        },
        'jquery_validate': {
            deps: ['jquery']
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
        },
        'bootstrap_tooltip': {
            deps: ['jquery']
        },
        'bootstrap_collapse': {
            deps: ['jquery']
        },
        'pagedown_converter': {
            exports: 'Markdown'
        },
        'pagedown_editor': {
            deps: ['pagedown_converter']
        },
        'pagedown_sanitizer': {
            deps: ['pagedown_editor']
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

