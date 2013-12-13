/**
 * Wikked views.
 */
define([
        'jquery',
        'underscore',
        'backbone',
        'handlebars',
        'bootstrap_tooltip',
        'bootstrap_collapse',
        'js/wikked/client',
        'js/wikked/models',
        'js/wikked/util',
        'text!tpl/read-page.html',
        'text!tpl/meta-page.html',
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
    function($, _, Backbone, Handlebars, BootstrapTooltip, BootstrapCollapse, Client, Models, Util,
        tplReadPage, tplMetaPage, tplEditPage, tplHistoryPage, tplRevisionPage, tplDiffPage, tplInLinksPage,
        tplNav, tplFooter, tplSearchResults, tplLogin,
        tplErrorNotAuthorized, tplErrorNotFound, tplErrorUnauthorizedEdit, tplStateWarning,
        tplSpecialNav, tplSpecialPages, tplSpecialChanges, tplSpecialOrphans) {

    var exports = {};

    // JQuery feature for watching size changes in a DOM element.
    jQuery.fn.watch = function(id, fn) {
        return this.each(function() {
            var self = this;
            var oldVal = self[id];
            $(self).data(
                'watch_timer',
                setInterval(
                    function() {
                        if (self[id] !== oldVal) {
                            fn.call(self, id, oldVal, self[id]);
                            oldVal = self[id];
                        }
                    },
                    100
                )
            );
        });
    };
    jQuery.fn.unwatch = function(id) {
        return this.each(function() {
            clearInterval($(this).data('watch_timer'));
        });
    };

    // Utility function to make wiki links into usable links for
    // this UI frontend.
    var processWikiLinks = function(el) {
        $('a.wiki-link', el).each(function(i) {
            var jel = $(this);
            var wiki_url = jel.attr('data-wiki-url').replace(/^\//, '');
            if (jel.hasClass('missing') || jel.attr('data-action') == 'edit')
                jel.attr('href', '/#/edit/' + wiki_url);
            else
                jel.attr('href', '/#/read/' + wiki_url);
        });
        $('a.wiki-meta-link', el).each(function(i) {
            var jel = $(this);
            var meta_name = jel.attr('data-wiki-meta');
            var meta_value = jel.attr('data-wiki-value');
            if (jel.hasClass('missing') || jel.attr('data-action') == 'edit')
                jel.attr('href', '/#/edit/' + meta_name + ':' + meta_value);
            else
                jel.attr('href', '/#/read/' + meta_name + ':' + meta_value);
        });
    };

    var PageView = exports.PageView = Backbone.View.extend({
        tagName: 'div',
        className: 'wrapper',
        isMainPage: true,
        initialize: function() {
            PageView.__super__.initialize.apply(this, arguments);
            if (this.model !== undefined) {
                var $view = this;
                this.model.on("change", function() { $view._onModelChange(); });
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
            if (this.template === undefined && this.templateSource !== undefined) {
                this.template = Handlebars.compile(_.result(this, 'templateSource'));
            }
            if (this.template !== undefined) {
                this.renderTemplate(this.template);
                if (this.renderCallback !== undefined) {
                    this.renderCallback();
                }
            }
            if (this.isMainPage) {
                this.renderTitle(this.titleFormat);
            }
            return this;
        },
        renderTemplate: function(tpl) {
            this.$el.html(tpl(this.model.toJSON()));
        },
        renderTitle: function(formatter) {
            var title = _.result(this, 'title');
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
        isMainPage: false,
        initialize: function() {
            NavigationView.__super__.initialize.apply(this, arguments);
            return this;
        },
        render: function() {
            NavigationView.__super__.render.apply(this, arguments);
            this.origPageEl = $('.wrapper>article');
            return this;
        },
        events: {
            "submit #search": "_submitSearch",
            "input #search-query": "_previewSearch",
            "keyup #search-query": "_searchQueryChanged"
        },
        _submitSearch: function(e) {
            e.preventDefault();
            this.model.doSearch(e.currentTarget);
            return false;
        },
        _previewSearch: function(e) {
            // Restore the original content if the query is now
            // empty. Otherwise, run a search and render only the
            // `article` portion of the results page.
            var origPageEl = this.origPageEl;
            var curPreviewEl = $('.wrapper>article[class~="preview-search-results"]');
            var query = $(e.currentTarget).val();
            if (query && query.length > 0) {
                var template = Handlebars.compile(tplSearchResults);
                this.model.doPreviewSearch(query, function(data) {
                    data.is_instant = true;
                    var resultList = $(template(data));
                    var inner = $(resultList)
                        .addClass('preview-search-results');
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
        isMainPage: false,
        initialize: function() {
            FooterView.__super__.initialize.apply(this, arguments);
            return this;
        },
        render: function() {
            FooterView.__super__.render.apply(this, arguments);
            return this;
        }
    });

    var LoginView = exports.LoginView = PageView.extend({
        templateSource: tplLogin,
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
            this.$el.prepend('<div class="nav-wrapper"></div>');
            this.$el.append('<div class="footer-wrapper"></div>');
            this.nav.setElement(this.$('>.nav-wrapper')).render();
            this.footer.setElement(this.$('>.footer-wrapper')).render();
            this.isError = (this.model.get('error_code') !== undefined);
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
            if (this.isError) {
                return;
            }

            processWikiLinks(this.$el);

            // If we've already rendered the content, see if we need to display a
            // warning about the page's state.
            if (this.model.get('content')) {
                if (this._pageState === undefined) {
                    if (!this._isCheckingPageState)
                        this._checkPageState();
                } else {
                    this._showPageStateWarning();
                }
            }
        },
        _showPageStateWarning: function() {
            if (this._pageState === undefined)
                return;

            var state = this._pageState.get('state');
            if (state == 'new' || state == 'modified') {
                var article = $('.wrapper>article');
                var warning = $(this.warningTemplate(this._pageState.toJSON()));
                $('[rel="tooltip"]', warning).tooltip({container:'body'});
                //warning.css('display', 'none');
                warning.prependTo(article);
                //warning.slideDown();
                $('.dismiss', warning).click(function() {
                    //warning.slideUp();
                    warning.remove();
                    return false;
                });
            }
        },
        _isCheckingPageState: false,
        _checkPageState: function() {
            this._isCheckingPageState = true;
            var $view = this;
            var statePath = this.model.checkStatePath();
            if (!statePath)
                return;
            var stateModel = new Models.PageStateModel({ path: statePath });
            stateModel.fetch({
                success: function(model, response, options) {
                    $view._pageState = model;
                    $view._isCheckingPageState = false;
                    if ($view.model && $view.model.get('content')) {
                        $view._showPageStateWarning();
                    }
                }
            });
        }
    });

    var PageEditView = exports.PageEditView = MasterPageView.extend({
        defaultTemplateSource: tplEditPage,
        dispose: function() {
            PageEditView.__super__.dispose.apply(this, arguments);
            this._removePreview();
        },
        renderCallback: function() {
            PageEditView.__super__.renderCallback.apply(this, arguments);
            if (this.isError) {
                return;
            }

            // Cache some stuff.
            this._ctrlInput = $('#wmd-input');
            this._ctrlPreview = $('#wmd-preview');
            this._originalInputHeight = this._ctrlInput.height();

            // Create the Markdown editor.
            var formatter = new Client.PageFormatter();
            formatter.baseUrl = this.model.get('path').match(/.*\//);
            var converter = new Markdown.Converter();
            converter.hooks.chain("preConversion", function(text) {
                return formatter.formatText(text);
            });
            var $view = this;
            var editor = new Markdown.Editor(converter); //TODO: pass options
            editor.hooks.chain("onPreviewRefresh", function() {
                $view._updateUI(true);
            });
            editor.run();

            // Setup UI.
            this._updateUI();
            $('#wmd-preview-wrapper').hide();
        },
        events: {
            "mousedown #wmd-input-grip": "_inputGripMouseDown",
            "click #wmd-preview-button": "_togglePreview",
            "click #wmd-full-preview-button": "_toggleFullPreview",
            "submit #page-edit": "_submitEditedPage"
        },
        _inputGripMouseDown: function(e) {
            // Input area resizing with the grip.
            var last_pageY;
            last_pageY = e.pageY;
            $('body')
                .on('mousemove.wikked.editor_resize', function(e) {
                    var editor_control = $('#wmd-input');
                    editor_control.height(editor_control.height() + e.pageY - last_pageY);
                    last_pageY = e.pageY;
                })
                .on('mouseup.wikked.editor_resize mouseleave.wikked.editor_resize', function(e) {
                    $('body').off('.wikked.editor_resize');
                });
        },
        _togglePreview: function(e) {
            // Show/hide live preview.
            var w = $('body').width() - 40;
            if (this._ctrlPreview.is(":visible")) {
                this._removePreview();
            } else {
                this._addPreview();
            }
            e.preventDefault();
            return false;
        },
        _addPreview: function() {
            $('#app')
                .removeClass('container')
                .addClass('container-fluid');
            $('#page-edit')
                .removeClass('row')
                .addClass('row-fluid');
            $('#wmd-form-wrapper')
                .removeClass('span12')
                .addClass('span6');
            $('#wmd-preview-wrapper')
                .show()
                .addClass('span6');

            this._updateUI(true);
        },
        _removePreview: function() {
            $('#wmd-form-wrapper')
                .removeClass('span6')
                .addClass('span12');
            $('#wmd-preview-wrapper')
                .hide()
                .removeClass('span6');
            $('#page-edit')
                .removeClass('row-fluid')
                .addClass('row');
            $('#app')
                .removeClass('container-fluid')
                .addClass('container');

            this._ctrlInput.height(this._originalInputHeight);
            this._updateUI();
        },
        _toggleFullPreview: function(e) {
            var $view = this;
            var previewData = {
                url: this.model.get('path'),
                text: $('#wmd-input').val()
            };
            $.post('/api/preview', previewData)
                .success(function(data) {
                    var previewEl = $('#wmd-preview');
                    previewEl.html(data.text);
                    processWikiLinks(previewEl);
                    $view._updateUI(true);
                })
                .error(function() {
                    $('#wmd-preview').html("Error running preview.");
                });
            e.preventDefault();
            return false;
        },
        _updateUI: function(setHeight) {
            var inputWidth = $('#wmd-input-wrapper').innerWidth();
            this._ctrlInput.outerWidth(inputWidth);

            if (setHeight === true) {
                var maxHeight = Math.max(
                    this._ctrlPreview.height(),
                    this._ctrlInput.height());
                this._ctrlInput.height(maxHeight);
            }
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
        className: 'wrapper special',
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
        renderCallback: function() {
            SpecialChangesView.__super__.renderCallback.apply(this, arguments);
            if (this.isError) {
                return;
            }

            this.$('.history-list .page-details').hide();
            this.$('.history-list .page-details-toggler').click(function (e) {
                index = $(this).attr('data-index');
                $('.history-list .page-details-' + index).toggle();
                e.preventDefault();
            });
        },
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

