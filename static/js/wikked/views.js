/**
 * Wikked views.
 */
define([
        'jquery',
        'underscore',
        'backbone',
        'handlebars',
        'js/wikked/client',
        'js/wikked/models',
        'js/wikked/util',
        'text!tpl/read-page.html',
        'text!tpl/edit-page.html',
        'text!tpl/history-page.html',
        'text!tpl/revision-page.html',
        'text!tpl/diff-page.html',
        'text!tpl/inlinks-page.html',
        'text!tpl/nav.html',
        'text!tpl/footer.html',
        'text!tpl/search-results.html',
        'text!tpl/login.html',
        'text!tpl/error-unauthorized.html',
        'text!tpl/error-not-found.html',
        'text!tpl/error-unauthorized-edit.html',
        'text!tpl/state-warning.html',
        'text!tpl/special-nav.html',
        'text!tpl/special-pages.html',
        'text!tpl/special-changes.html',
        'text!tpl/special-orphans.html'
        ],
    function($, _, Backbone, Handlebars, Client, Models, Util,
        tplReadPage, tplEditPage, tplHistoryPage, tplRevisionPage, tplDiffPage, tplInLinksPage,
        tplNav, tplFooter, tplSearchResults, tplLogin,
        tplErrorNotAuthorized, tplErrorNotFound, tplErrorUnauthorizedEdit, tplStateWarning,
        tplSpecialNav, tplSpecialPages, tplSpecialChanges, tplSpecialOrphans) {

    var exports = {};

    var PageView = exports.PageView = Backbone.View.extend({
        tagName: 'div',
        className: 'wrapper',
        initialize: function() {
            PageView.__super__.initialize.apply(this, arguments);
            if (this.model !== undefined) {
                var $view = this;
                this.model.on("change", function() { $view._onModelChange(); });
            }
            if (this.templateSource !== undefined) {
                this.template = Handlebars.compile(_.result(this, 'templateSource'));
            }
            return this;
        },
        dispose: function() {
            this.remove();
            this.unbind();
            if (this.model) {
                this.model.unbind();
            }
            if (this._onDispose) {
                this._onDispose();
            }
        },
        render: function(view) {
            if (this.template !== undefined) {
                this.renderTemplate(this.template);
                if (this.renderCallback !== undefined) {
                    this.renderCallback();
                }
            }
            this.renderTitle(this.titleFormat);
            return this;
        },
        renderTemplate: function(tpl) {
            this.$el.html(tpl(this.model.toJSON()));
        },
        renderTitle: function(formatter) {
            var title = this.model.title();
            if (formatter !== undefined) {
                title = formatter.call(this, title);
            }
            document.title = title;
        },
        _onModelChange: function() {
            this.render();
        }
    });
    _.extend(PageView, Backbone.Events);

    var NavigationView = exports.NavigationView = PageView.extend({
        templateSource: tplNav,
        initialize: function() {
            NavigationView.__super__.initialize.apply(this, arguments);
            return this;
        },
        render: function() {
            this.renderTemplate(this.template);
            this.origPageEl = $('#app .page');
            return this;
        },
        events: {
            "submit #search": "_submitSearch",
            "input #search>.search-query": "_previewSearch",
            "keyup #search>.search-query": "_searchQueryChanged"
        },
        _submitSearch: function(e) {
            e.preventDefault();
            this.model.doSearch(e.currentTarget);
            return false;
        },
        _previewSearch: function(e) {
            // Restore the original content if the query is now
            // empty. Otherwise, run a search and render only the
            // `.page` portion of the results page.
            var origPageEl = this.origPageEl;
            var curPreviewEl = $('#app .page[class~="preview-search-results"]');
            var query = $(e.currentTarget).val();
            if (query && query.length > 0) {
                var template = Handlebars.compile(tplSearchResults);
                this.model.doPreviewSearch(query, function(data) {
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
        },
        _searchQueryChanged: function(e) {
            if (e.keyCode == 27) {
                // Clear search on `Esc`.
                $(e.currentTarget).val('').trigger('input');
            }
        }
    });

    var FooterView = exports.FooterView = PageView.extend({
        templateSource: tplFooter,
        initialize: function() {
            FooterView.__super__.initialize.apply(this, arguments);
            return this;
        },
        render: function() {
            this.renderTemplate(this.template);
            return this;
        }
    });

    var LoginView = exports.LoginView = PageView.extend({
        templateSource: tplLogin,
        initialize: function() {
            LoginView.__super__.initialize.apply(this, arguments);
            return this;
        },
        render: function() {
            this.renderTemplate(this.template);
            document.title = 'Login';
            return this;
        },
        events: {
            "submit #login": "_submitLogin"
        },
        _submitLogin: function(e) {
            e.preventDefault();
            this.model.doLogin(e.currentTarget);
            return false;
        }
    });

    var MasterPageView = exports.MasterPageView = PageView.extend({
        initialize: function() {
            MasterPageView.__super__.initialize.apply(this, arguments);
            this.nav = this._createNavigation(this.model.nav);
            this.footer = this._createFooter(this.model.footer);
            return this;
        },
        renderCallback: function() {
            this.$el.prepend('<div id="nav"></div>');
            this.$el.append('<div id="footer"></div>');
            this.nav.setElement(this.$('#nav')).render();
            this.footer.setElement(this.$('#footer')).render();
        },
        templateSource: function() {
            switch (this.model.get('error_code')) {
                case 401:
                    return tplErrorNotAuthorized;
                case 404:
                    return tplErrorNotFound;
                default:
                    return _.result(this, 'defaultTemplateSource');
            }
        },
        _createNavigation: function(model) {
            return new NavigationView({ model: model });
        },
        _createFooter: function(model) {
            return new FooterView({ model: model });
        }
    });

    var PageReadView = exports.PageReadView = MasterPageView.extend({
        defaultTemplateSource: tplReadPage,
        initialize: function() {
            PageReadView.__super__.initialize.apply(this, arguments);
            this.warningTemplate = Handlebars.compile(tplStateWarning);
            return this;
        },
        renderCallback: function() {
            PageReadView.__super__.renderCallback.apply(this, arguments);
            // Replace all wiki links with proper hyperlinks using the JS app's
            // URL scheme.
            this.$('a.wiki-link[data-wiki-url]').each(function(i) {
                var jel = $(this);
                if (jel.hasClass('missing') || jel.attr('data-action') == 'edit')
                    jel.attr('href', '/#/edit/' + jel.attr('data-wiki-url'));
                else
                    jel.attr('href', '/#/read/' + jel.attr('data-wiki-url'));
            });
            // If we've already rendered the content, and we need to display
            // a warning, do so now.
            if (this.model.get('content')) {
                this._showPageStateWarning();
            }
        },
        _showPageStateWarning: function() {
            if (this._pageState === undefined)
                return;

            var state = this._pageState.get('state');
            if (state == 'new' || state == 'modified') {
                var warning = $(this.warningTemplate(this._pageState.toJSON()));
                warning.css('display', 'none');
                warning.prependTo($('#app .page'));
                warning.slideDown();
                $('.dismiss', warning).click(function() {
                    warning.slideUp();
                    return false;
                });
            }
        },
        _checkPageState: function() {
            var $view = this;
            var stateModel = new Models.PageStateModel({ path: this.model.get('path') });
            stateModel.fetch({
                success: function(model, response, options) {
                    $view._pageState = model;
                    // If we've already rendered the content, display
                    // the warning, if any, now.
                    if ($view.model && $view.model.get('content')) {
                        $view._showPageStateWarning();
                    }
                }
            });
        },
        _firstRender: true,
        _onModelChange: function() {
            PageReadView.__super__._onModelChange.apply(this, arguments);

            // Fetch the state if the current page changed.
            if (this.model.hasChanged('path') || this._firstRender) {
                this._checkPageState();
                this._firstRender = false;
            }
        }
    });

    var PageEditView = exports.PageEditView = MasterPageView.extend({
        templateSource: function() {
            if (this.model.get('error_code') == 401) {
                return tplErrorUnauthorizedEdit;
            }
            return tplEditPage;
        },
        renderCallback: function() {
            PageEditView.__super__.renderCallback.apply(this, arguments);

            // Create the Markdown editor.
            var formatter = new Client.PageFormatter();
            formatter.baseUrl = this.model.get('path').match(/.*\//);
            var converter = new Markdown.Converter();
            converter.hooks.chain("preConversion", function(text) {
                return formatter.formatText(text);
            });
            var editor = new Markdown.Editor(converter); //TODO: pass options
            editor.run();
            var editor_control = this.$('textarea#wmd-input');
            editor_control.outerWidth(this.$('.wmd-input-wrapper').innerWidth());
        },
        events: {
            "mousedown .wmd-input-grip": "_inputGripMouseDown",
            "click .wmd-preview-wrapper>h3>a": "_togglePreview",
            "submit #page-edit": "_submitEditedPage"
        },
        _inputGripMouseDown: function(e) {
            // Input area resizing with the grip.
            var last_pageY;
            last_pageY = e.pageY;
            $('body')
                .on('mousemove.wikked.editor_resize', function(e) {
                    var editor_control = $('textarea#wmd-input');
                    editor_control.height(editor_control.height() + e.pageY - last_pageY);
                    last_pageY = e.pageY;
                })
                .on('mouseup.wikked.editor_resize mouseleave.wikked.editor_resize', function(e) {
                    $('body').off('.wikked.editor_resize');
                });
        },
        _togglePreview: function(e) {
            // Show/hide live preview.
            this.$('#wmd-preview').fadeToggle(function() {
                var icon = this.$('.wmd-preview-wrapper>h3>a i');
                if (icon.hasClass('icon-minus')) {
                    icon.removeClass('icon-minus');
                    icon.addClass('icon-plus');
                } else {
                    icon.removeClass('icon-plus');
                    icon.addClass('icon-minus');
                }
            });
        },
        _submitEditedPage: function(e) {
            // Make the model submit the form.
            e.preventDefault();
            this.model.doEdit(e.currentTarget);
            return false;
        },
        titleFormat: function(title) {
            return 'Editing: ' + title;
        }
    });

    var PageHistoryView = exports.PageHistoryView = MasterPageView.extend({
        defaultTemplateSource: tplHistoryPage,
        events: {
            "submit #diff-page": "_submitDiffPage"
        },
        _submitDiffPage: function(e) {
            e.preventDefault();
            this.model.doDiff(e.currentTarget);
            return false;
        },
        titleFormat: function(title) {
            return 'History: ' + title;
        }
    });

    var PageRevisionView = exports.PageRevisionView = MasterPageView.extend({
        defaultTemplateSource: tplRevisionPage,
        titleFormat: function(title) {
            return title + ' [' + this.model.get('rev') + ']';
        },
        events: {
            "submit #page-revert": "_submitPageRevert"
        },
        _submitPageRevert: function(e) {
            e.preventDefault();
            this.model.doRevert(e.currentTarget);
            return false;
        }
    });

    var PageDiffView = exports.PageDiffView = MasterPageView.extend({
        defaultTemplateSource: tplDiffPage,
        titleFormat: function(title) {
            return title + ' [' + this.model.get('rev1') + '-' + this.model.get('rev2') + ']';
        }
    });

    var IncomingLinksView = exports.IncomingLinksView = MasterPageView.extend({
        defaultTemplateSource: tplInLinksPage,
        titleFormat: function(title) {
            return 'Incoming Links: ' + title;
        }
    });

    var WikiSearchView = exports.WikiSearchView = MasterPageView.extend({
        defaultTemplateSource: tplSearchResults
    });

    var SpecialNavigationView = exports.SpecialNavigationView = NavigationView.extend({
        templateSource: tplSpecialNav
    });

    var SpecialMasterPageView = exports.SpecialMasterPageView = MasterPageView.extend({
        _createNavigation: function(model) {
            model.set('show_root_link', true);
            return new SpecialNavigationView({ model: model });
        }
    });

    var SpecialPagesView = exports.SpecialPagesView = SpecialMasterPageView.extend({
        defaultTemplateSource: tplSpecialPages
    });

    var SpecialChangesView = exports.SpecialChangesView = SpecialMasterPageView.extend({
        defaultTemplateSource: tplSpecialChanges,
        _onModelChange: function() {
            var history = this.model.get('history');
            if (history) {
                for (var i = 0; i < history.length; ++i) {
                    var rev = history[i];
                    rev.changes = [];
                    for (var j = 0; j < rev.pages.length; ++j) {
                        var page = rev.pages[j];
                        switch (page.action) {
                            case 'edit':
                                rev.changes.push({ is_edit: true, url: page.url });
                                break;
                            case 'add':
                                rev.changes.push({ is_add: true, url: page.url });
                                break;
                            case 'delete':
                                rev.changes.push({ is_delete: true, url: page.url });
                                break;
                        }
                        rev.pages[j] = page;
                    }
                    history[i] = rev;
                }
                this.model.set('history', history);
            }
            SpecialChangesView.__super__._onModelChange.apply(this, arguments);
        }
    });

    var SpecialOrphansView = exports.SpecialOrphansView = SpecialMasterPageView.extend({
        defaultTemplateSource: tplSpecialOrphans
    });

    return exports;
});

