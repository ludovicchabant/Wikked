/**
 * Handlebars helpers and extensions.
 */
define([
        'handlebars',
        'moment'
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
     * 
     */
    Handlebars.registerHelper('each_or_this', function(context, options) {
        if (context === undefined) {
            return '';
        }
        data = undefined;
        if (options.data) {
            data = Handlebars.createFrame(options.data);
        }
        var out = '';
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
    Handlebars.registerHelper('date', function(timestamp, options) {
        var date = new Date(timestamp * 1000);
        if ("format" in options.hash) {
            return moment(date).format(options.hash.format);
        }
        return moment(date).format();
    });
    Handlebars.registerHelper('date_from_now', function(timestamp, options) {
        var date = new Date(timestamp * 1000);
        return moment(date).fromNow();
    });
});

