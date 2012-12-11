/**
 * Make Javascript suck less.
 */
String.prototype.format = function() {
    var args = arguments;
    return this.replace(/{(\d+)}/g, function(match, number) { 
        return typeof args[number] != 'undefined'
            ? args[number]
            : match
            ;
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
        _onChangePath: function(path) {
            this.set('url_home', '/#/read/main-page');
            this.set('url_read', '/#/read/' + path);
            this.set('url_edit', '/#/edit/' + path);
            this.set('url_hist', '/#/changes/' + path);
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

    /**
     * Wiki page views.
     */
    var PageReadView = Backbone.View.extend({
        tagName: "div",
        initialize: function() {
            var $view = this;
            var model = new PageModel({ path: this.id });
            console.log('Loading page: {0}'.format(model.get('path')));
            model.fetch({
                success: function(model, response, options) {
                    TemplateLoader.get('read-page', function(src) {
                        var template_data = model.toJSON();
                        var template = Handlebars.compile(src);
                        $view.$el.html(template(template_data));
                        $('a.wiki-link[data-wiki-url]').each(function(i, el) {
                            var jel = $(el);
                            jel.attr('href', '/#/read/' + jel.attr('data-wiki-url'));
                        });
                        document.title = model.get('title');
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
                    console.log('Got state: ' + model.get('state'));
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
            console.log('Loading page "{0}" for edit.'.format(model.get('path')));
            model.fetch({
                success: function(model, response, options) {
                    TemplateLoader.get('edit-page', function(src) {
                        var template_data = model.toJSON();
                        var template = Handlebars.compile(src);
                        $view.$el.html(template(template_data));
                        document.title = 'Editing: ' + model.get('title');

                        $('#page-edit').submit(function() {
                            console.log('Submitting: ' + $(this).serialize());
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
                    console.log("Edit successful, navigating back to: " + path);
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
            console.log('Loading history for page: ' + model.get('path'));
            model.fetch({
                success: function(model, response, options) {
                    TemplateLoader.get('history-page', function(src) {
                        var template_data = model.toJSON();
                        var template = Handlebars.compile(src);
                        $view.$el.html(template(template_data));
                        document.title = 'Changes: ' + model.get('title');
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
            'read/*path':   "readPage",
            '':             "readMainPage",
            'edit/*path':   "editPage",
            'changes/*path':"showPageHistory"
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
        }
    });

    /**
     * Launch!
     */
    var app = new AppRouter;
    Backbone.history.start();//{ pushState: true });
});

