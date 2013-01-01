/**
 * Wikked views.
 */
define([
        'jquery',
        'underscore',
        'backbone',
        'handlebars',
        './models',
        './util'
        ],
    function($, _, Backbone, Handlebars, Models, Util) {

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
            Util.TemplateLoader.get(tpl_name, function(src) {
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
            var model = this.model;
            this.$('#search').submit(function(e) {
                e.preventDefault();
                model.doSearch(this);
                return false;
            });
            var $view = this;
            Util.TemplateLoader.get('search-results', function(src) {
                var template = Handlebars.compile(src);
                var origPageEl = $('#app .page');

                $view.$('#search .search-query')
                    .on('input', function() {
                        var curPreviewEl = $('#app .page[class~="preview-search-results"]');

                        // Restore the original content if the query is now
                        // empty. Otherwise, run a search and render only the
                        // `.page` portion of the results page.
                        var query = $(this).val();
                        if (query && query.length > 0) {
                            model.doPreviewSearch(query, function(data) {
                                data.is_instant = true;
                                var resultList = $(template(data));
                                var inner = $('.page', resultList)
                                    .addClass('preview-search-results')
                                    .detach();
                                if (origPageEl.is(':visible')) {
                                    inner.insertAfter(origPageEl);
                                    origPageEl.hide();
                                } else {
                                    curPreviewEl.replaceWith(inner);
                                }
                            });
                        } else {
                            curPreviewEl.remove();
                            origPageEl.show();
                        }
                    })
                    .keyup(function(e) {
                        if (e.keyCode == 27) {
                            // Clear search on `Esc`.
                            $(this).val('').trigger('input');
                        }
                    });
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

    var LoginView = PageView.extend({
        templateName: 'login',
        initialize: function() {
            LoginView.__super__.initialize.apply(this, arguments);
            this.render();
            return this;
        },
        render: function() {
            this.renderTemplate('login', function(view, model) {
                this.$('#login').submit(function(e) {
                    e.preventDefault();
                    model.doLogin(this);
                    return false;
                });
            });
            document.title = 'Login';
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
            var stateModel = new Models.PageStateModel({ path: this.model.get('path') });
            stateModel.fetch({
                success: function(model, response, options) {
                    if (model.get('state') == 'new' || model.get('state') == 'modified') {
                        Util.TemplateLoader.get('state-warning', function(src) {
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
            this.$('#page-edit').submit(function(e) {
                e.preventDefault();
                model.doEdit(this);
                return false;
            });
        },
        titleFormat: function(title) {
            return 'Editing: ' + title;
        }
    });

    var PageHistoryView = MasterPageView.extend({
        templateName: 'history-page',
        renderCallback: function(view, model) {
            PageHistoryView.__super__.renderCallback.apply(this, arguments);
            this.$('#diff-page').submit(function(e) {
                e.preventDefault();
                model.doDiff(this);
                return false;
            });
        },
        titleFormat: function(title) {
            return 'History: ' + title;
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

    return {
        PageReadView: PageReadView,
        PageEditView: PageEditView,
        PageHistoryView: PageHistoryView,
        IncomingLinksView: IncomingLinksView,
        PageRevisionView: PageRevisionView,
        PageDiffView: PageDiffView,
        WikiSearchView: WikiSearchView,
        LoginView: LoginView
    };
});

