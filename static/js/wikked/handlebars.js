/**
 * Handlebars helpers and extensions.
 */
define([
        'handlebars'
        ],
    function(Handlebars) {

    /**
     * Handlebars helper: reverse iterator.
     */
    Handlebars.registerHelper('eachr', function(context, options) {
        if (context === undefined) {
            return '';
        }
        data = undefined;
        if (options.data) {
            data = Handlebars.createFrame(options.data);
        }
        var out = '';
        for (var i=context.length - 1; i >= 0; i--) {
            if (data !== undefined) {
                data.index = (context.length - 1 - i);
                data.rindex = i;
            }
            out += options.fn(context[i], { data: data });
        }
        return out;
    });

    /**
     * Would you believe Handlebars doesn't have an equality
     * operator?
     */
    Handlebars.registerHelper('ifeq', function(context, options) {
        if (context == options.hash.to) {
            return options.fn(this);
        }
        return options.inverse(this);
    });
    Handlebars.registerHelper('ifneq', function(context, options) {
        if (context != options.hash.to) {
            return options.fn(this);
        }
        return options.inverse(this);
    });

    /**
     * Inverse if.
     */
    Handlebars.registerHelper('ifnot', function(context, options) {
        if (!context) {
            return options.fn(this);
        }
        return options.inverse(this);
    });

    /**
     * Format dates.
     */
    Handlebars.registerHelper('date', function(timestamp) {
        var date = new Date(timestamp * 1000);
        return date.toDateString();
    });
});

