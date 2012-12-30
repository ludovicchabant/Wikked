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
            console.log('Returning cached template "{0}".'.format(name));
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
        text = text.replace(/^\[\[([a-z]+)\:\s*(.+)\]\]\s*$/m, function(m, a, b) {
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

//-------------------------------------------------------------//

/**
 * Start the main app once the page is loaded.
 */
$(function() {

    /**
     * Wiki page models.
     */
    var NavigationModel = Backbone.Model.extend({
        idAttribute: 'path',
        defaults: function() {
            return {
                path: "main-page",
                action: "read"
            };
        },
        initialize: function() {
            this.on('change:path', function(model, path) {
                model._onChangePath(path);
            });
            this._onChangePath(this.get('path'));
            return this;
        },
        _onChangePath: function(path) {
            this.set('url_home', '/#/read/main-page');
            this.set('url_read', '/#/read/' + path);
            this.set('url_edit', '/#/edit/' + path);
            this.set('url_hist', '/#/changes/' + path);
            this.set('url_search', '/search');
        }
    });

    var FooterModel = Backbone.Model.extend({
        defaults: function() {
            return {
                url_extras: [ { name: 'Home', url: '/' } ]
            };
        },
        addExtraUrl: function(name, url, index) {
            if (index === undefined) {
                this.get('url_extras').push({ name: name, url: url });
            } else {
                this.get('url_extras').splice(index, 0, { name: name, url: url });
            }
        }
    });

    var PageModel = Backbone.Model.extend({
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
            return this;
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
        },
        _onChangeText: function(text) {
            this.set('content', new Handlebars.SafeString(text));
        }
    });
    
    var PageStateModel = PageModel.extend({
        urlRoot: '/api/state/'
    });
    
    var MasterPageModel = PageModel.extend({
        initialize: function() {
            this.nav = new NavigationModel({ id: this.id });
            this.footer = new FooterModel();
            MasterPageModel.__super__.initialize.apply(this, arguments);
            if (this.action !== undefined) {
                this.nav.set('action', this.action);
                this.footer.set('action', this.action);
            }
            return this;
        },
        _onChangePath: function(path) {
            MasterPageModel.__super__._onChangePath.apply(this, arguments);
            this.nav.set('path', path);
        }
    });

    var PageReadModel = MasterPageModel.extend({
        urlRoot: '/api/read/',
        action: 'read',
        _onChangePath: function(path) {
            PageReadModel.__super__._onChangePath.apply(this, arguments);
            this.footer.addExtraUrl('Pages Linking Here', '/#/inlinks/' + path, 1);
            this.footer.addExtraUrl('JSON', '/api/read/' + path);
        }
    });

    var PageSourceModel = MasterPageModel.extend({
        urlRoot: '/api/raw/',
        action: 'source'
    });

    var PageEditModel = MasterPageModel.extend({
        urlRoot: '/api/edit/',
        action: 'edit'
    });

    var PageHistoryModel = MasterPageModel.extend({
        urlRoot: '/api/history/',
        action: 'history',
        _onChangePath: function(path) {
            PageHistoryModel.__super__._onChangePath.apply(this, arguments);
            this.set('url_rev', '/#/revision/' + path);
            this.set('url_diffc', '/#/diff/c/' + path);
            this.set('url_diffr', '/#/diff/r/' + path);
        }
    });

    var PageRevisionModel = MasterPageModel.extend({
        urlRoot: '/api/revision/',
        idAttribute: 'path_and_rev',
        action: 'revision',
        defaults: function() {
            return {
                path: "main-page",
                rev: "tip"
            };
        },
        initialize: function() {
            PageRevisionModel.__super__.initialize.apply(this, arguments);
            this.on('change:path', function(model, path) {
                model._onChangePathOrRev(path, model.get('rev'));
            });
            this.on('change:rev', function(model, rev) {
                model._onChangePathOrRev(model.get('path'), rev);
            });
            this._onChangePathOrRev(this.get('path'), this.get('rev'));
            return this;
        },
        _onChangePathOrRev: function(path, rev) {
            this.set('path_and_rev', path + '/' + rev);
            this.set('disp_rev', rev);
            if (rev.match(/[a-f0-9]{40}/)) {
                this.set('disp_rev', rev.substring(0, 8));
            }
        }
    });

    var PageDiffModel = MasterPageModel.extend({
        urlRoot: '/api/diff/',
        idAttribute: 'path_and_revs',
        action: 'diff',
        defaults: function() {
            return {
                path: "main-page",
                rev1: "tip",
                rev2: ""
            };
        },
        initialize: function() {
            PageDiffModel.__super__.initialize.apply(this, arguments);
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
            return this;
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

    var IncomingLinksModel = MasterPageModel.extend({
        urlRoot: '/api/inlinks/',
        action: 'inlinks'
    });

    var WikiSearchModel = MasterPageModel.extend({
        urlRoot: '/api/search/',
        action: 'search',
        title: function() {
            return 'Search';
        },
        execute: function(query) {
            var $model = this;
            $.getJSON('/api/search', { q: query })
                .success(function (data) {
                    $model.set('hits', data.hits);
                })
                .error(function() {
                    alert("Error searching...");
                });
        }
    });

    /**
     * Wiki page views.
     */
    var PageView = Backbone.View.extend({
        tagName: 'div',
        className: 'wrapper',
        initialize: function() {
            PageView.__super__.initialize.apply(this, arguments);
            var $view = this;
            this.model.on("change", function() { $view.render(); });
            return this;
        },
        render: function(view) {
            if (this.templateName !== undefined) {
                this.renderTemplate(this.templateName, this.renderCallback);
            }
            this.renderTitle(this.titleFormat);
            return this;
        },
        renderTemplate: function(tpl_name, callback) {
            var $view = this;
            TemplateLoader.get(tpl_name, function(src) {
                var template = Handlebars.compile(src);
                $view.$el.html(template($view.model.toJSON()));
                if (callback !== undefined) {
                    callback.call($view, $view, $view.model);
                }
            });
        },
        renderTitle: function(formatter) {
            var title = this.model.title();
            if (formatter !== undefined) {
                title = formatter.call(this, title);
            }
            document.title = title;
        }
    });
    _.extend(PageView, Backbone.Events);

    var NavigationView = PageView.extend({
        templateName: 'nav',
        initialize: function() {
            NavigationView.__super__.initialize.apply(this, arguments);
            this.render();
            return this;
        },
        render: function() {
            this.renderTemplate('nav');
        },
        postRender: function() {
            var $view = this;
            this.$('#search').submit(function() {
                app.navigate('/search/' + $(this.q).val(), { trigger: true });
                return false;
            });
        }
    });

    var FooterView = PageView.extend({
        templateName:  'footer',
        initialize: function() {
            FooterView.__super__.initialize.apply(this, arguments);
            this.render();
            return this;
        },
        render: function() {
            this.renderTemplate('footer');
        },
        postRender: function() {
        }
    });

    var MasterPageView = PageView.extend({
        initialize: function() {
            MasterPageView.__super__.initialize.apply(this, arguments);
            this.nav = new NavigationView({ model: this.model.nav });
            this.footer = new FooterView({ model: this.model.footer });
            this.render();
            return this;
        },
        renderCallback: function(view, model) {
            this.nav.$el.prependTo(this.$el);
            this.nav.postRender();
            this.footer.$el.appendTo(this.$el);
            this.footer.postRender();
        }
    });

    var PageReadView = MasterPageView.extend({
        templateName: 'read-page',
        initialize: function() {
            PageReadView.__super__.initialize.apply(this, arguments);
            // Also get the current state, and show a warning
            // if the page is new or modified.
            var stateModel = new PageStateModel({ path: this.model.get('path') });
            stateModel.fetch({
                success: function(model, response, options) {
                    if (model.get('state') == 'new' || model.get('state') == 'modified') {
                        TemplateLoader.get('state-warning', function(src) {
                            var template = Handlebars.compile(src);
                            var warning = $(template(model.toJSON()));
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
        },
        renderCallback: function(view, model) {
            PageReadView.__super__.renderCallback.apply(this, arguments);
            // Replace all wiki links with proper hyperlinks using the JS app's
            // URL scheme.
            this.$('a.wiki-link[data-wiki-url]').each(function(i) {
                var jel = $(this);
                if (jel.hasClass('missing'))
                    jel.attr('href', '/#/edit/' + jel.attr('data-wiki-url'));
                else
                    jel.attr('href', '/#/read/' + jel.attr('data-wiki-url'));
            });
        }
    });

    var PageEditView = MasterPageView.extend({
        templateName: 'edit-page',
        renderCallback: function(view, model) {
            PageEditView.__super__.renderCallback.apply(this, arguments);
            this.$('#page-edit').submit(function() {
                view._submitText(this, model.get('path'));
                return false;
            });
        },
        titleFormat: function(title) {
            return 'Editing: ' + title;
        },
        _submitText: function(form, path) {
            $.post('/api/edit/' + path, this.$(form).serialize())
                .success(function(data) {
                    app.navigate('/read/' + path, { trigger: true });
                })
                .error(function() {
                    alert('Error saving page...');
                });
        }
    });

    var PageHistoryView = MasterPageView.extend({
        templateName: 'history-page',
        renderCallback: function(view, model) {
            PageHistoryView.__super__.renderCallback.apply(this, arguments);
            this.$('#diff-page').submit(function() {
                view._triggerDiff(this, model.get('path'));
                return false;
            });
        },
        titleFormat: function(title) {
            return 'History: ' + title;
        },
        _triggerDiff: function(form, path) {
            var rev1 = $('input[name=rev1]:checked', form).val();
            var rev2 = $('input[name=rev2]:checked', form).val();
            app.navigate('/diff/r/' + path + '/' + rev1 + '/' + rev2, { trigger: true });
        }
    });

    var PageRevisionView = MasterPageView.extend({
        templateName: 'revision-page',
        titleFormat: function(title) {
            return title + ' [' + this.model.get('rev') + ']';
        }
    });

    var PageDiffView = MasterPageView.extend({
        templateName: 'diff-page',
        titleFormat: function(title) {
            return title + ' [' + this.model.get('rev1') + '-' + this.model.get('rev2') + ']';
        }
    });

    var IncomingLinksView = MasterPageView.extend({
        templateName: 'inlinks-page',
        titleFormat: function(title) {
            return 'Incoming Links: ' + title;
        }
    });

    var WikiSearchView = MasterPageView.extend({
        templateName: 'search-results'
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
            'diff/r/*path/:rev1/:rev2':"showDiff",
            'search/:query':         "showSearchResults"
        },
        readPage: function(path) {
            var view = new PageReadView({ 
                el: $('#app'), 
                model: new PageReadModel({ path: path })
            });
            view.model.fetch();
            this.navigate('/read/' + path);
        },
        readMainPage: function() {
            this.readPage('main-page');
        },
        editPage: function(path) {
            var view = new PageEditView({ 
                el: $('#app'),
                model: new PageEditModel({ path: path })
            });
            view.model.fetch();
            this.navigate('/edit/' + path);
        },
        showPageHistory: function(path) {
            var view = new PageHistoryView({
                el: $('#app'),
                model: new PageHistoryModel({ path: path })
            });
            view.model.fetch();
            this.navigate('/changes/' + path);
        },
        showIncomingLinks: function(path) {
            var view = new IncomingLinksView({
                el: $('#app'),
                model: new IncomingLinksModel({ path: path })
            });
            view.model.fetch();
            this.navigate('/inlinks/' + path);
        },
        readPageRevision: function(path, rev) {
            var view = new PageRevisionView({
                el: $('#app'),
                rev: rev, 
                model: new PageRevisionModel({ path: path, rev: rev })
            });
            view.model.fetch();
            this.navigate('/revision/' + path + '/' + rev);
        },
        showDiffWithPrevious: function(path, rev) {
            var view = new PageDiffView({
                el: $('#app'),
                rev1: rev,
                model: new PageDiffModel({ path: path, rev1: rev })
            });
            view.model.fetch();
            this.navigate('/diff/c/' + path + '/' + rev);
        },
        showDiff: function(path, rev1, rev2) {
            var view = new PageDiffView({
                el: $('#app'),
                rev1: rev1,
                rev2: rev2,
                model: new PageDiffModel({ path: path, rev1: rev1, rev2: rev2 })
            });
            view.model.fetch();
            this.navigate('/diff/r/' + path + '/' + rev1 + '/' + rev2);
        },
        showSearchResults: function(query) {
            if (query === '') {
                query = this.getQueryVariable('q');
            }
            var view = new WikiSearchView({
                el: $('#app'),
                model: new WikiSearchModel()
            });
            view.model.execute(query);
            this.navigate('/search/' + query);
        },
        getQueryVariable: function(variable) {
            var query = window.location.search.substring(1);
            var vars = query.split("&");
            for (var i = 0; i < vars.length; i++) {
                var pair = vars[i].split("=");
                if (pair[0] == variable) {
                    return unescape(pair[1]);
                }
            }
            return false;
        }
    });

    /**
     * Launch!
     */
    var app = new AppRouter();
    Backbone.history.start();//{ pushState: true });
});

