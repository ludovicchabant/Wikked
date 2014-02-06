/**
 * Client-side Wikked.
 */
define([
        'jquery',
        'underscore'
        ],
    function($, _) {

    /**
     * Function to normalize an array of path parts (remove/simplify `./` and
     * `../` elements).
     */
    function normalizeArray(parts, keepBlanks) {
        var directories = [], prev;
        for (var i = 0, l = parts.length - 1; i <= l; i++) {
            var directory = parts[i];

            // if it's blank, but it's not the first thing, and not the last thing, skip it.
            if (directory === "" && i !== 0 && i !== l && !keepBlanks)
                continue;

            // if it's a dot, and there was some previous dir already, then skip it.
            if (directory === "." && prev !== undefined)
                continue;

            // if it starts with "", and is a . or .., then skip it.
            if (directories.length === 1 && directories[0] === "" && (
                directory === "." || directory === ".."))
                continue;

                if (
                    directory === ".." && directories.length && prev !== ".." && prev !== "." && prev !== undefined && (prev !== "" || keepBlanks)) {
                    directories.pop();
                prev = directories.slice(-1)[0];
            } else {
                if (prev === ".") directories.pop();
                directories.push(directory);
                prev = directory;
            }
        }
        return directories;
    }

    /**
     * Client-side page formatter, with support for previewing meta properties
     * in the live preview window.
     */
    var PageFormatter = function(baseUrl) {
        this.baseUrl = baseUrl;
        if (baseUrl === undefined) {
            this.baseUrl = '';
        }
    };
    _.extend(PageFormatter.prototype, {
        formatLink: function(link) {
            var abs_link = link;
            if (link[0] == '/') {
                abs_link = link.substring(1);
            } else {
                raw_abs_link = this.baseUrl + link;
                abs_link = normalizeArray(raw_abs_link.split('/')).join('/');
            }
            return encodeURI(abs_link);
        },
        formatText: function(text) {
            var $f = this;
            text = text.replace(
                /^\{\{((__|\+)?[a-zA-Z][a-zA-Z0-9_\-]+)\:\s*(.*)\}\}\s*$/gm,
                function(m, a, b, c) {
                    if (!c) {
                        c = 'true';
                    }
                    var p = "<p><span class=\"preview-wiki-meta\">\n";
                    p += "<span class=\"meta-name\">" + a + "</span>";
                    p += "<span class=\"meta-value\">" + c + "</span>\n";
                    p += "</span></p>\n\n";
                    return p;
            });
            text = text.replace(/\[\[([^\|\]]+)\|([^\]]+)\]\]/g, function(m, a, b) {
                var url = $f.formatLink(b);
                return '[' + a + '](/#/read/' + url + ')';
            });
            text = text.replace(/\[\[([^\]]+\/)?([^\]]+)\]\]/g, function(m, a, b) {
                var url = $f.formatLink(a + b);
                return '[' + b + '](/#/read/' + url + ')';
            });
            return text;
        }
    });

    return {
        PageFormatter: PageFormatter
    };
});

