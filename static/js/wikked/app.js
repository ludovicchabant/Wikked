/**
 * The main Wikked app/router.
 */
define([
        'jquery',
        'underscore',
        'backbone',
        './views',
        './models'
        ],
    function($, _, Backbone, Views, Models) {

    /**
     * Main router.
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
                el: $('#app'),
                model: new Models.PageReadModel({ path: path_clean })
            });
            if (no_redirect) {
                view.model.set('no_redirect', true);
            }
            view.model.setApp(this);
            view.model.fetch();
            this.navigate('/read/' + path);
        },
        readMainPage: function() {
            this.readPage('main-page');
        },
        editPage: function(path) {
            var view = new Views.PageEditView({
                el: $('#app'),
                model: new Models.PageEditModel({ path: path })
            });
            view.model.setApp(this);
            view.model.fetch();
            this.navigate('/edit/' + path);
        },
        showPageHistory: function(path) {
            var view = new Views.PageHistoryView({
                el: $('#app'),
                model: new Models.PageHistoryModel({ path: path })
            });
            view.model.setApp(this);
            view.model.fetch();
            this.navigate('/changes/' + path);
        },
        showIncomingLinks: function(path) {
            var view = new Views.IncomingLinksView({
                el: $('#app'),
                model: new Models.IncomingLinksModel({ path: path })
            });
            view.model.setApp(this);
            view.model.fetch();
            this.navigate('/inlinks/' + path);
        },
        readPageRevision: function(path, rev) {
            var view = new Views.PageRevisionView({
                el: $('#app'),
                rev: rev,
                model: new Models.PageRevisionModel({ path: path, rev: rev })
            });
            view.model.setApp(this);
            view.model.fetch();
            this.navigate('/revision/' + path + '/' + rev);
        },
        showDiffWithPrevious: function(path, rev) {
            var view = new Views.PageDiffView({
                el: $('#app'),
                rev1: rev,
                model: new Models.PageDiffModel({ path: path, rev1: rev })
            });
            view.model.setApp(this);
            view.model.fetch();
            this.navigate('/diff/c/' + path + '/' + rev);
        },
        showDiff: function(path, rev1, rev2) {
            var view = new Views.PageDiffView({
                el: $('#app'),
                rev1: rev1,
                rev2: rev2,
                model: new Models.PageDiffModel({ path: path, rev1: rev1, rev2: rev2 })
            });
            view.model.setApp(this);
            view.model.fetch();
            this.navigate('/diff/r/' + path + '/' + rev1 + '/' + rev2);
        },
        showSearchResults: function(query) {
            if (query === '') {
                query = this.getQueryVariable('q');
            }
            var view = new Views.WikiSearchView({
                el: $('#app'),
                model: new Models.WikiSearchModel()
            });
            view.model.setApp(this);
            view.model.execute(query);
            this.navigate('/search/' + query);
        },
        showLogin: function() {
            var view = new Views.LoginView({
                el: $('#app'),
                model: new Models.LoginModel()
            });
            view.model.setApp(this);
            view.render();
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
                el: $('#app'),
                model: new Models.SpecialPagesModel()
            });
            view.model.setApp(this);
            view.render();
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
                el: $('#app'),
                model: new Models.GenericSpecialPageModel({ page: page })
            });
            view.model.setApp(this);
            view.model.fetch();
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

