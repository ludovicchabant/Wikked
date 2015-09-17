/**
 * RequireJS configuration.
 *
 * We need to alias/shim some of the libraries.
 */
require.config({
    paths: {
        jquery: 'jquery-1.8.3.min',
        jquery_validate: 'jquery/jquery.validate.min',
        underscore: 'underscore-min',
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
        }
    }
});

