/**
 * Handlebars helpers and extensions.
 */
define([
        'handlebars',
        'moment'
        ],
    function(Handlebars) {

    /**
     * Reverse iterator.
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
     * Concatenate strings with a separator.
     */
    Handlebars.registerHelper('concat', function(context, options) {
        if (context === undefined) {
            return '';
        }
        data = undefined;
        if (options.data) {
            data = Handlebars.createFrame(options.data);
        }

        var sep = options.hash.sep;
        var out = '';
        for (var i = 0; i < context.length; i++) {
            if (i > 0) {
                out += sep;
            }
            out += options.fn(context[i], { data: data });
        }
        return out;
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

    /**
     * Format application URLs
     */
    Handlebars.registerHelper('get_read_url', function(url, options) {
        url = url.toString();
        return '/#/read/' + url.replace(/^\//, '');
    });
    Handlebars.registerHelper('get_edit_url', function(url, options) {
        url = url.toString();
        return '/#/edit/' + url.replace(/^\//, '');
    });
    Handlebars.registerHelper('get_cat_url', function(url, options) {
        url = url.toString();
        return '/#/meta/category/' + url.replace(/^\//, '');
    });
});

