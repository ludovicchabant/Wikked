/**
 * Client-side Wikked.
 */
define(function() {

    var PageFormatter = {
        formatLink: function(link) {
            return link.toLowerCase().replace(/[^a-z0-9_\.\-\(\)\/]+/g, '-');
        },
        formatText: function(text) {
            var $f = this;
            text = text.replace(/^\[\[([a-z]+)\:\s*(.+)\]\]\s*$/gm, function(m, a, b) {
                var p = "<p><span class=\"preview-wiki-meta\">\n";
                p += "<span class=\"meta-name\">" + a + "</span>";
                p += "<span class=\"meta-value\">" + b + "</span>\n";
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
    };
    //TODO: remove this and move the JS code from the template to the view.
    if (!window.Wikked)
        window.Wikked = {};
    window.Wikked.PageFormatter = PageFormatter;

    return {
        PageFormatter: PageFormatter
    };
});

