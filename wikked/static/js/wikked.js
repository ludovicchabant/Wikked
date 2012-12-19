/**
 * Make Javascript suck less.
 */
String.prototype.format = function() {
    var args = arguments;
    return this.replace(/\{(\d+)\}/g, function(match, number) { 
        return typeof args[number] != 'undefined' ? args[number] : match;
    });
};

this.Wikked = {};

/**
 * Helper class to load template files
 * by name from the `tpl` directory.
 */
var TemplateLoader = Wikked.TemplateLoader = {
    loadedTemplates: {},
    get: function(name, callback) {
        if (name in this.loadedTemplates) {
            callback(this.loadedTemplates[name]);
        } else {
            var $loader = this;
            url = '/tpl/' + name + '.html' + '?' + (new Date()).getTime();
            console.log('Loading template "{0}" from: {1}'.format(name, url));
            $.get(url, function(data) {
                $loader.loadedTemplates[name] = data;
                callback(data);
            });
        }
    }
};

//-------------------------------------------------------------//

/**
 * Handlebars helper: reverse iterator.
 */
Handlebars.registerHelper('eachr', function(context, options) {
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

//-------------------------------------------------------------//

/**
 * Client-side Wikked.
 */
var PageFormatter = Wikked.PageFormatter = {
    formatLink: function(link) {
        return link.toLowerCase().replace(/[^a-z0-9_\.\-\(\)\/]+/g, '-');
    },
    formatText: function(text) {
        var $f = this;
        text = text.replace(/\[\[([a-z]+)\:\s*(.+)\]\]\s*$/m, 
            '<p class="preview-wiki-meta">$1 = $2</p>\n\n');
        text = text.replace(/\[\[([^\|\]]+)\|([^\]]+)\]\]/g, function(m, a, b) {
            url = $f.formatLink(b);
            return '[' + a + '](/#/read/' + url + ')';
        });
        text = text.replace(/\[\[([^\]]+\/)?([^\]]+)\]\]/g, function(m, a, b) {
            url = $f.formatLink(a + b);
            return '[' + b + '](/#/read/' + url + ')';
        });
        return text;
    }
};

//-------------------------------------------------------------//

/**
 * Start the main app once the page is loaded.
 */
$(function() {

    /**
     * Wiki page models.
     */
    var PageModel = Backbone.Model.extend({
        urlRoot: '/api/read/',
        idAttribute: 'path',
        defaults: function() {
            return {
                path: "main-page"
            };
        },
        initialize: function() {
            this.on('change:path', function(model, path) {
                model._onChangePath(path);
            });
            this.on('change:text', function(model, text) {
                model._onChangeText(text);
            });
            this._onChangePath(this.get('path'));
            this._onChangeText('');
        },
        url: function() {
            var base = _.result(this, 'urlRoot') || _.result(this.collection, 'url') || urlError();
            if (this.isNew()) return base;
            return base + (base.charAt(base.length - 1) === '/' ? '' : '/') + this.id;
        },
        title: function() {
            return this.getMeta('title');
        },
        getMeta: function(key) {
            var meta = this.get('meta');
            if (meta === undefined) {
                return undefined;
            }
            return meta[key];
        },
        _onChangePath: function(path) {
            this.set('url_home', '/#/read/main-page');
            this.set('url_read', '/#/read/' + path);
            this.set('url_edit', '/#/edit/' + path);
            this.set('url_hist', '/#/changes/' + path);
            this.set('url_rev', '/#/revision/' + path);
            this.set('url_diffc', '/#/diff/c/' + path);
            this.set('url_diffr', '/#/diff/r/' + path);
            this.set('url_inlinks', '/#/inlinks/' + path);
        },
        _onChangeText: function(text) {
            this.set('content', new Handlebars.SafeString(text));
        }
    });
    
    var PageStateModel = PageModel.extend({
        urlRoot: '/api/state/'
    });

    var PageSourceModel = PageModel.extend({
        urlRoot: '/api/raw/'
    });

    var PageEditModel = PageModel.extend({
        urlRoot: '/api/edit/'
    });

    var PageHistoryModel = PageModel.extend({
        urlRoot: '/api/history/'
    });

    var PageRevisionModel = PageModel.extend({
        urlRoot: '/api/revision/',
        idAttribute: 'path_and_rev',
        defaults: function() {
            return {
                path: "main-page",
                rev: "tip"
            };
        },
        initialize: function() {
            this.on('change:path', function(model, path) {
                model._onChangePathOrRev(path, model.get('rev'));
            });
            this.on('change:rev', function(model, rev) {
                model._onChangePathOrRev(model.get('path'), rev);
            });
            this._onChangePathOrRev(this.get('path'), this.get('rev'));
            PageRevisionModel.__super__.initialize.call(this);
        },
        _onChangePathOrRev: function(path, rev) {
            this.set('path_and_rev', path + '/' + rev);
            this.set('disp_rev', rev);
            if (rev.match(/[a-f0-9]{40}/)) {
                this.set('disp_rev', rev.substring(0, 8));
            }
        }
    });

    var PageDiffModel = PageModel.extend({
        urlRoot: '/api/diff/',
        idAttribute: 'path_and_revs',
        defaults: function() {
            return {
                path: "main-page",
                rev1: "tip",
                rev2: ""
            };
        },
        initialize: function() {
            this.on('change:path', function(model, path) {
                model._onChangePathOrRevs(path, model.get('rev'));
            });
            this.on('change:rev1', function(model, rev1) {
                model._onChangePathOrRevs(model.get('path'), rev1, model.get('rev2'));
            });
            this.on('change:rev2', function(model, rev2) {
                model._onChangePathOrRevs(model.get('path'), model.get('rev1'), rev2);
            });
            this._onChangePathOrRevs(this.get('path'), this.get('rev1'), this.get('rev2'));
            PageRevisionModel.__super__.initialize.call(this);
        },
        _onChangePathOrRevs: function(path, rev1, rev2) {
            this.set('path_and_revs', path + '/' + rev1 + '/' + rev2);
            if (!rev2) {
                this.set('path_and_revs', path + '/' + rev1);
            }
            this.set('disp_rev1', rev1);
            if (rev1 !== undefined && rev1.match(/[a-f0-9]{40}/)) {
                this.set('disp_rev1', rev1.substring(0, 8));
            }
            this.set('disp_rev2', rev2);
            if (rev2 !== undefined && rev2.match(/[a-f0-9]{40}/)) {
                this.set('disp_rev2', rev2.substring(0, 8));
            }
        }
    });

    var IncomingLinksModel = PageModel.extend({
        urlRoot: '/api/inlinks/'
    });

    /**
     * Wiki page views.
     */
    var PageReadView = Backbone.View.extend({
        tagName: "div",
        initialize: function() {
            var $view = this;
            var model = new PageModel({ path: this.id });
            model.fetch({
                success: function(model, response, options) {
                    TemplateLoader.get('read-page', function(src) {
                        var template_data = model.toJSON();
                        var template = Handlebars.compile(src);
                        $view.$el.html(template(template_data));
                        $('a.wiki-link[data-wiki-url]').each(function(i, el) {
                            var jel = $(el);
                            if (jel.hasClass('missing'))
                                jel.attr('href', '/#/edit/' + jel.attr('data-wiki-url'));
                            else
                                jel.attr('href', '/#/read/' + jel.attr('data-wiki-url'));
                        });
                        document.title = model.title();
                    });
                },
                error: function(model, xhr, options) {
                    TemplateLoader.get('404', function(src) {
                        var template = _.template(src);
                        $view.$el.html(template());
                    });
                }
            });
            // Also get the current state, and show a warning
            // if the page is new or modified.
            var stateModel = new PageStateModel({ id: this.id });
            stateModel.fetch({
                success: function(model, response, options) {
                    if (model.get('state') == 'new' || model.get('state') == 'modified') {
                        TemplateLoader.get('state-warning', function(src) {
                            var template_data = model.toJSON();
                            var template = Handlebars.compile(src);
                            var warning = $(template(template_data));
                            warning.css('display', 'none');
                            warning.prependTo($('#app'));
                            warning.slideDown();
                            $('.dismiss', warning).click(function() {
                                warning.slideUp();
                                return false;
                            });
                        });
                    }
                }
            });
            return this;
        }
    });

    var PageEditView = Backbone.View.extend({
        initialize: function() {
            var $view = this;
            var model = new PageEditModel({ path: this.id });
            model.fetch({
                success: function(model, response, options) {
                    TemplateLoader.get('edit-page', function(src) {
                        var template_data = model.toJSON();
                        var template = Handlebars.compile(src);
                        $view.$el.html(template(template_data));
                        document.title = 'Editing: ' + model.title();

                        $('#page-edit').submit(function() {
                            $view._submitText(this, model.get('path'));
                            return false;
                        });
                    });
                },
                error: function(model, xhr, options) {
                }
            });
            return this;
        },
        _submitText: function(form, path) {
            $.post('/api/edit/' + path, $(form).serialize())
                .success(function(data) {
                    app.navigate('/read/' + path, { trigger: true });
                })
                .error(function() {
                    alert('Error saving page...');
                });
        }
    });

    var PageHistoryView = Backbone.View.extend({
        initialize: function() {
            var $view = this;
            var model = new PageHistoryModel({ path: this.id });
            model.fetch({
                success: function(model, response, options) {
                    TemplateLoader.get('history-page', function(src) {
                        var template_data = model.toJSON();
                        var template = Handlebars.compile(src);
                        $view.$el.html(template(template_data));
                        document.title = 'Changes: ' + model.title();

                        $('#diff-page').submit(function() {
                            $view._triggerDiff(this, model.get('path'));
                            return false;
                        });
                    });
                },
                error: function() {
                }
            });
            return this;
        },
        _triggerDiff: function(form, path) {
            var rev1 = $('input[name=rev1]:checked', form).val();
            var rev2 = $('input[name=rev2]:checked', form).val();
            app.navigate('/diff/r/' + path + '/' + rev1 + '/' + rev2, { trigger: true });
        }
    });

    var PageRevisionView = Backbone.View.extend({
        initialize: function() {
            var $view = this;
            var model = new PageRevisionModel({ path: this.id, rev: this.options.rev });
            model.fetch({
                success: function(model, response, options) {
                    TemplateLoader.get('revision-page', function(src) {
                        var template_data = model.toJSON();
                        var template = Handlebars.compile(src);
                        $view.$el.html(template(template_data));
                        document.title = model.title() + ' [' + model.get('rev') + ']';
                    });
                }
            });
        }
    });

    var PageDiffView = Backbone.View.extend({
        initialize: function() {
            var $view = this;
            var model = new PageDiffModel({ path: this.id, rev1: this.options.rev1, rev2: this.options.rev2 });
            model.fetch({
                success: function(model, response, options) {
                    TemplateLoader.get('diff-page', function(src) {
                        var template_data = model.toJSON();
                        var template = Handlebars.compile(src);
                        $view.$el.html(template(template_data));
                        document.title = model.title() + ' [' + model.get('rev1') + '-' + model.get('rev2') + ']';
                    });
                }
            });
        }
    });

    var IncomingLinksView = Backbone.View.extend({
        initialize: function() {
            var $view = this;
            var model = new IncomingLinksModel({ path: this.id });
            model.fetch({
                success: function(model, response, options) {
                    TemplateLoader.get('inlinks-page', function(src) {
                        var template_data = model.toJSON();
                        var template = Handlebars.compile(src);
                        $view.$el.html(template(template_data));
                        document.title = 'Incoming Links: ' + model.title();
                    });
                },
                error: function() {
                }
            });
            return this;
        }
    });

    /**
     * Main URL router.
     */
    var AppRouter = Backbone.Router.extend({
        routes: {
            'read/*path':           "readPage",
            '':                     "readMainPage",
            'edit/*path':           "editPage",
            'changes/*path':        "showPageHistory",
            'inlinks/*path':        "showIncomingLinks",
            'revision/*path/:rev':  "readPageRevision",
            'diff/c/*path/:rev':    "showDiffWithPrevious",
            'diff/r/*path/:rev1/:rev2':"showDiff"
        },
        readPage: function(path) {
            var page_view = new PageReadView({ id: path, el: $('#app') });
            this.navigate('/read/' + path);
        },
        readMainPage: function() {
            this.readPage('main-page');
        },
        editPage: function(path) {
            var edit_view = new PageEditView({ id: path, el: $('#app') });
            this.navigate('/edit/' + path);
        },
        showPageHistory: function(path) {
            var changes_view = new PageHistoryView({ id: path, el: $('#app') });
            this.navigate('/changes/' + path);
        },
        showIncomingLinks: function(path) {
            var in_view = new IncomingLinksView({ id: path, el: $('#app') });
            this.navigate('/inlinks/' + path);
        },
        readPageRevision: function(path, rev) {
            var rev_view = new PageRevisionView({ id: path, rev: rev, el: $('#app') });
            this.navigate('/revision/' + path + '/' + rev);
        },
        showDiffWithPrevious: function(path, rev) {
            var diff_view = new PageDiffView({ id: path, rev1: rev, el: $('#app') });
            this.navigate('/diff/c/' + path + '/' + rev);
        },
        showDiff: function(path, rev1, rev2) {
            var diff_view = new PageDiffView({ id: path, rev1: rev1, rev2: rev2, el: $('#app') });
            this.navigate('/diff/r/' + path + '/' + rev1 + '/' + rev2);
        }
    });

    /**
     * Launch!
     */
    var app = new AppRouter();
    Backbone.history.start();//{ pushState: true });
});

