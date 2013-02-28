/**
 * The main Wikked app/router.
 */
define([
        'jquery',
        'underscore',
        'backbone',
        'js/wikked/views',
        'js/wikked/models'
        ],
    function($, _, Backbone, Views, Models) {

    var exports = {};

    /**
     * View manager.
     */
    var ViewManager = exports.ViewManager = function(el) {
        this.initialize.apply(this, arguments);
    };
    _.extend(ViewManager.prototype, {
        initialize: function(el) {
            this.el = el;
        },
        _currentView: false,
        switchView: function(view, autoFetch) {
            if (this._currentView) {
                this._currentView.dispose();
                this._currentView = false;
            }

            if (view) {
                this._currentView = view;
                this.el.html(view.el);
                if (autoFetch || autoFetch === undefined) {
                    view.model.fetch();
                } else {
                    view.render();
                }
            }

            return this;
        }
    });

    /**
     * Main router.
     */
    var AppRouter = Backbone.Router.extend({
        initialize: function(options) {
            this.viewManager = options ? options.viewManager : undefined;
            if (!this.viewManager) {
                this.viewManager = new ViewManager($('#app'));
            }

            var $router = this;
            Backbone.View.prototype.navigate = function(url, options) {
                $router.navigate(url, options);
            };
            Backbone.Model.prototype.navigate = function(url, options) {
                $router.navigate(url, options);
            };
        },
        routes: {
            'read/*path':           "readPage",
            '':                     "readMainPage",
            'edit/*path':           "editPage",
            'changes/*path':        "showPageHistory",
            'inlinks/*path':        "showIncomingLinks",
            'revision/*path/:rev':  "readPageRevision",
            'diff/c/*path/:rev':    "showDiffWithPrevious",
            'diff/r/*path/:rev1/:rev2':"showDiff",
            'search/:query':         "showSearchResults",
            'login':                 "showLogin",
            'logout':                "doLogout",
            'special':               "showSpecialPages",
            'special/:page':         "showSpecialPage"
        },
        readPage: function(path) {
            path_clean = this.stripQuery(path);
            no_redirect = this.getQueryVariable('no_redirect', path);
            var view = new Views.PageReadView({
                model: new Models.PageReadModel({ path: path_clean })
            });
            if (no_redirect) {
                view.model.set('no_redirect', true);
            }
            this.viewManager.switchView(view);
            this.navigate('/read/' + path);
        },
        readMainPage: function() {
            this.readPage('main-page');
        },
        editPage: function(path) {
            var view = new Views.PageEditView({
                model: new Models.PageEditModel({ path: path })
            });
            this.viewManager.switchView(view);
            this.navigate('/edit/' + path);
        },
        showPageHistory: function(path) {
            var view = new Views.PageHistoryView({
                model: new Models.PageHistoryModel({ path: path })
            });
            this.viewManager.switchView(view);
            this.navigate('/changes/' + path);
        },
        showIncomingLinks: function(path) {
            var view = new Views.IncomingLinksView({
                model: new Models.IncomingLinksModel({ path: path })
            });
            this.viewManager.switchView(view);
            this.navigate('/inlinks/' + path);
        },
        readPageRevision: function(path, rev) {
            var view = new Views.PageRevisionView({
                rev: rev,
                model: new Models.PageRevisionModel({ path: path, rev: rev })
            });
            this.viewManager.switchView(view);
            this.navigate('/revision/' + path + '/' + rev);
        },
        showDiffWithPrevious: function(path, rev) {
            var view = new Views.PageDiffView({
                rev1: rev,
                model: new Models.PageDiffModel({ path: path, rev1: rev })
            });
            this.viewManager.switchView(view);
            this.navigate('/diff/c/' + path + '/' + rev);
        },
        showDiff: function(path, rev1, rev2) {
            var view = new Views.PageDiffView({
                rev1: rev1,
                rev2: rev2,
                model: new Models.PageDiffModel({ path: path, rev1: rev1, rev2: rev2 })
            });
            this.viewManager.switchView(view);
            this.navigate('/diff/r/' + path + '/' + rev1 + '/' + rev2);
        },
        showSearchResults: function(query) {
            if (query === '') {
                query = this.getQueryVariable('q');
            }
            var view = new Views.WikiSearchView({
                model: new Models.WikiSearchModel()
            });
            this.viewManager.switchView(view);
            this.navigate('/search/' + query);
        },
        showLogin: function() {
            var view = new Views.LoginView({
                model: new Models.LoginModel()
            });
            this.viewManager.switchView(view);
            this.navigate('/login');
        },
        doLogout: function() {
            var $app = this;
            $.post('/api/user/logout')
                .success(function(data) {
                    $app.navigate('/', { trigger: true });
                })
                .error(function() {
                    alert("Error logging out!");
                });
        },
        showSpecialPages: function() {
            var view = new Views.SpecialPagesView({
                model: new Models.SpecialPagesModel()
            });
            this.viewManager.switchView(view, false);
            this.navigate('/special');
        },
        showSpecialPage: function(page) {
            var viewType = false;
            switch (page) {
                case "changes":
                    viewType = Views.SpecialChangesView;
                    break;
                case "orphans":
                    viewType = Views.SpecialOrphansView;
                    break;
            }
            if (viewType === false) {
                console.error("Unsupported special page: ", page);
                return;
            }
            var view = new viewType({
                model: new Models.GenericSpecialPageModel({ page: page })
            });
            this.viewManager.switchView(view);
            this.navigate('/special/' + page);
        },
        stripQuery: function(url) {
            q = url.indexOf("?");
            if (q < 0)
                return url;
            return url.substring(0, q);
        },
        getQueryVariable: function(variable, url) {
            if (url === undefined) {
                url = window.location.search.substring(1);
            } else {
                q = url.indexOf("?");
                if (q < 0)
                    return false;
                url = url.substring(q + 1);
            }
            var vars = url.split("&");
            for (var i = 0; i < vars.length; i++) {
                var pair = vars[i].split("=");
                if (pair[0] == variable) {
                    if (pair.length > 1) {
                        return unescape(pair[1]);
                    } else {
                        return true;
                    }
                }
            }
            return false;
        }
    });

    return {
        Router: AppRouter
    };
});

