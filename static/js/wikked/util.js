/**
 * Various utility classes/functions.
 */
define([
        'jquery'
        ],
    function($) {

    /**
     * Make Javascript suck less.
     */
    String.prototype.format = function() {
        var args = arguments;
        return this.replace(/\{(\d+)\}/g, function(match, number) { 
            return typeof args[number] != 'undefined' ? args[number] : match;
        });
    };

    /**
     * Helper class to load template files
     * by name from the `tpl` directory.
     */
    var TemplateLoader = {
        loadedTemplates: {},
        get: function(name, callback) {
            if (name in this.loadedTemplates) {
                callback(this.loadedTemplates[name]);
            } else {
                var $loader = this;
                url = '/tpl/' + name + '.html' + '?' + (new Date()).getTime();
                $.get(url, function(data) {
                    $loader.loadedTemplates[name] = data;
                    callback(data);
                });
            }
        }
    };

    return {
        TemplateLoader: TemplateLoader
    };
});

