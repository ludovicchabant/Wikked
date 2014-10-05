/**
 * Wikked models.
 */
define([
        'require',
        'jquery',
        'underscore',
        'backbone',
        'handlebars'
        ],
    function(require, $, _, Backbone, Handlebars) {

    var exports = {};

    var NavigationModel = exports.NavigationModel = Backbone.Model.extend({
        defaults: function() {
            return {
                path: "",
                username: false,
                urls: [],
                url_extras: [
                    { name: 'Special Pages', url: '/#/special', icon: 'dashboard' }
                ]
            };
        },
        initialize: function() {
            this.on('change:path', this._onChangePath, this);
            this.on('change:user', this._onChangeUser, this);
            this._onChangePath(this, this.get('path'));
            this._onChangeUser(this, this.get('user'));
            return this;
        },
        url: function() {
            return '/api/user/info';
        },
        clearExtraUrls: function() {
            this.get('url_extras').length = 0;
        },
        addExtraUrl: function(name, url, index, icon) {
            extra = { name: name, url: url, icon: icon };
            if (index === undefined || index < 0) {
                this.get('url_extras').push(extra);
            } else {
                this.get('url_extras').splice(index, 0, extra);
            }
        },
        doPreviewSearch: function(query, callback) {
            if (this._isSearching) {
                this._pendingQuery = query;
                this._pendingCallback = callback;
                return;
            }
            this._isSearching = true;
            var $model = this;
            $.getJSON('/api/searchpreview', { q: query })
                .done(function (data) {
                    $model._isSearching = false;
                    callback(data);
                    $model._flushPendingQuery();
                })
                .fail(function() {
                    $model._isSearching = false;
                    $model._flushPendingQuery();
                });
        },
        doSearch: function(form) {
            this.navigate('/search/' + $(form.q).val(), { trigger: true });
        },
        doGoToSearchResult: function(url) {
            this.navigate(url + "?no_redirect", { trigger: true });
        },
        doNewPage: function(form) {
            this.navigate('/create/', { trigger: true });
        },
        _onChangePath: function(model, path) {
            var attrs ={
                url_home: '/#/'};
            var urls = this.get('urls');
            if (_.contains(urls, 'read'))
                attrs.url_read = '/#/read/' + path;
            if (_.contains(urls, 'edit'))
                attrs.url_edit = '/#/edit/' + path;
            if (_.contains(urls, 'history'))
                attrs.url_hist = '/#/changes/' + path;
            this.set(attrs);
        },
        _isSearching: false,
        _pendingQuery: null,
        _pendingCallback: null,
        _flushPendingQuery: function() {
            if (this._pendingQuery && this._pendingCallback) {
                var q = this._pendingQuery;
                var c = this._pendingCallback;
                this._pendingQuery = null;
                this._pendingCallback = null;
                this.doPreviewSearch(q, c);
            }
        },
        _onChangeUser: function(model, user) {
            if (user) {
                this.set({
                    url_login: false,
                    url_logout: '/#/logout',
                    url_profile: ('/#/read/' + user.page_url)
                });
            } else {
                this.set({
                    url_login: '/#/login',
                    url_logout: false,
                    url_profile: false
                });
            }
        }
    });

    var FooterModel = exports.FooterModel = Backbone.Model.extend({
        defaults: function() {
            return {
                url_extras: []
            };
        },
        clearExtraUrls: function() {
            this.get('url_extras').length = 0;
        },
        addExtraUrl: function(name, url, index, icon) {
            extra = { name: name, url: url, icon: icon };
            if (index === undefined || index < 0) {
                this.get('url_extras').push(extra);
            } else {
                this.get('url_extras').splice(index, 0, extra);
            }
        }
    });

    var LoginModel = exports.LoginModel = Backbone.Model.extend({
        title: 'Login',
        setApp: function(app) {
            this.app = app;
        },
        doLogin: function(form) {
            var $model = this;
            $.post('/api/user/login', $(form).serialize())
                .done(function() {
                    $model.navigate('/', { trigger: true });
                })
                .fail(function() {
                    $model.set('has_error', true);
                });
        }
    });

    var PageModel = exports.PageModel = Backbone.Model.extend({
        idAttribute: 'path',
        defaults: function() {
            return {
                path: ""
            };
        },
        initialize: function() {
            this.on('change:path', this._onChangePath, this);
            this.on('change:text', this._onChangeText, this);
            this._onChangePath(this, this.get('path'));
            this._onChangeText(this, '');
            return this;
        },
        url: function() {
            var base = _.result(this, 'urlRoot') || _.result(this.collection, 'url') || Backbone.urlError();
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
        setApp: function(app) {
            this.app = app;
            if (this._onAppSet !== undefined) {
                this._onAppSet(app);
            }
        },
        _onChangePath: function(model, path) {
        },
        _onChangeText: function(model, text) {
            this.set('content', new Handlebars.SafeString(text));
        }
    });

    var PageStateModel = exports.PageStateModel = PageModel.extend({
        urlRoot: '/api/state/',
        _onChangePath: function(model, path) {
            PageStateModel.__super__._onChangePath.apply(this, arguments);
            this.set('url_edit', '/#/edit/' + path);
        }
    });

    var MasterPageModel = exports.MasterPageModel = PageModel.extend({
        navUrls: [],
        initialize: function() {
            var navAttrs = { path: this.id, urls: this.navUrls };
            this.nav = new NavigationModel(navAttrs);
            this.footer = new FooterModel();
            MasterPageModel.__super__.initialize.apply(this, arguments);
            this._addNavExtraUrls();
            this._addFooterExtraUrls();
            this.on('change:auth', this._onChangeAuth, this);
            this.on('error', this._onError, this);
            return this;
        },
        _addNavExtraUrls: function() {
        },
        _addFooterExtraUrls: function() {
            var model = this;
            this.footer.addExtraUrl(
                'JSON',
                function() { return _.result(model, 'url'); },
                -1,
                'cog');
        },
        _onAppSet: function(app) {
            this.nav.app = app;
            this.footer.app = app;
        },
        _onChangePath: function(model, path) {
            MasterPageModel.__super__._onChangePath.apply(this, arguments);
            this.nav.set('path', path);
        },
        _onChangeAuth: function(model, auth) {
            this.nav.set('auth', auth);
        },
        _onError: function(model, resp) {
            var setmap = {
                has_error: true,
                error_code: resp.status
            };
            switch (resp.status) {
                case 401:
                    setmap.error = 'Unauthorized';
                    break;
                case 404:
                    setmap.error = 'Not Found';
                    break;
                default:
                    setmap.error = 'Error';
                    break;
            }
            this.set(setmap);
        }
    });

    var PageReadModel = exports.PageReadModel = MasterPageModel.extend({
        urlRoot: '/api/read/',
        navUrls: ['edit', 'history'],
        initialize: function() {
            PageReadModel.__super__.initialize.apply(this, arguments);
            this.on('change', this._onChange, this);
            return this;
        },
        _addNavExtraUrls: function() {
            PageReadModel.__super__._addNavExtraUrls.apply(this, arguments);
            var model = this;
            this.nav.addExtraUrl(
                'Pages Linking Here',
                function() { return '/#/inlinks/' + model.id; },
                1,
                'link');
        },
        _addFooterExtraUrls: function() {
            PageReadModel.__super__._addFooterExtraUrls.apply(this, arguments);
            var model = this;
            this.footer.addExtraUrl(
                'RAW',
                function() { return '/api/raw/' + model.id; },
                -1,
                'wrench');
        },
        url: function() {
            var url = PageReadModel.__super__.url.apply(this, arguments);
            var qs = {};
            if (!this.nav.get('user'))
                qs.user = 1;
            if (this.get('no_redirect'))
                qs.no_redirect = 1;
            if (_.size(qs) > 0)
                url += '?' + $.param(qs);
            return url;
        },
        checkStatePath: function() {
            return this.get('path');
        },
        _onChange: function() {
            if (this.get('user')) {
                // Forward user info to the navigation model.
                this.nav.set('user', this.get('user'));
            }
        }
    });

    var PageSourceModel = exports.PageSourceModel = MasterPageModel.extend({
        urlRoot: '/api/raw/'
    });

    var PageEditModel = exports.PageEditModel = MasterPageModel.extend({
        urlRoot: '/api/edit/',
        navUrls: ['read', 'history'],
        doEdit: function(form) {
            if (this.get('is_new')) {
                this.set('path', $('input[name="title"]', form).val());
            }

            var $model = this;
            $.post(this.url(), $(form).serialize(), null, 'json')
                .done(function(data) {
                    $model._onEditSuccess();
                })
                .fail(function(jqxhr) {
                    var err = $.parseJSON(jqxhr.responseText);
                    $model.set('error', err.error);
                });
        },
        doCancel: function() {
            this._goToReadPage();
        },
        _onEditSuccess: function() {
            this._goToReadPage();
        },
        _goToReadPage: function() {
            this.navigate('/read/' + this.get('path') + '?no_redirect',
                    { trigger: true });
        }
    });

    var PageHistoryModel = exports.PageHistoryModel = MasterPageModel.extend({
        urlRoot: '/api/history/',
        navUrls: ['read', 'edit'],
        doDiff: function(form) {
            var rev1 = $('input[name=rev1]:checked', form).val();
            var rev2 = $('input[name=rev2]:checked', form).val();
            this.navigate('/diff/r/' + this.get('path') + '/' + rev1 + '/' + rev2, { trigger: true });
        },
        _onChangePath: function(path) {
            PageHistoryModel.__super__._onChangePath.apply(this, arguments);
            this.set({
                url_read: '/#/read/' + path,
                url_edit: '/#/edit/' + path,
                url_rev: '/#/revision/' + path,
                url_diffc: '/#/diff/c/' + path,
                url_diffr: '/#/diff/r/' + path
            });
        }
    });

    var PageRevisionModel = exports.PageRevisionModel = MasterPageModel.extend({
        defaults: function() {
            return {
                path: "",
                rev: "tip"
            };
        },
        url: function() {
            return '/api/revision/' + this.get('path') + '?rev=' + this.get('rev');
        },
        initialize: function() {
            PageRevisionModel.__super__.initialize.apply(this, arguments);
            this.on('change:rev', this._onChangeRev, this);
            this._onChangeRev(this, this.get('rev'));
            return this;
        },
        doRevert: function(form) {
            var $model = this;
            var path = this.get('path');
            $.post('/api/revert/' + path, $(form).serialize())
                .success(function(data) {
                    $model.navigate('/read/' + path, { trigger: true });
                })
                .error(function() {
                    alert('Error reverting page...');
                });
        },
        _onChangeRev: function(model, rev) {
            var setmap = { disp_rev: rev };
            if (rev.match(/[a-f0-9]{40}/)) {
                setmap.disp_rev = rev.substring(0, 8);
            }
            this.set(setmap);
        }
    });

    var PageDiffModel = exports.PageDiffModel = MasterPageModel.extend({
        defaults: function() {
            return {
                path: "",
                rev1: "tip",
                rev2: ""
            };
        },
        url: function() {
            var apiUrl = '/api/diff/' + this.get('path') + '?rev1=' + this.get('rev1');
            if (this.get('rev2')) {
                apiUrl += '&rev2=' + this.get('rev2');
            }
            return apiUrl;
        },
        initialize: function() {
            PageDiffModel.__super__.initialize.apply(this, arguments);
            this.on('change:rev1', this._onChangeRev1, this);
            this.on('change:rev2', this._onChangeRev2, this);
            this._onChangeRev1(this, this.get('rev1'));
            this._onChangeRev2(this, this.get('rev2'));
            return this;
        },
        _onChangeRev1: function(model, rev1) {
            var setmap = { disp_rev1: rev1 };
            if (rev1 !== undefined && rev1.match(/[a-f0-9]{40}/)) {
                setmap.disp_rev1 = rev1.substring(0, 8);
            }
            this.set(setmap);
        },
        _onChangeRev2: function(model, rev2) {
            var setmap = { disp_rev2:  rev2 };
            if (rev2 !== undefined && rev2.match(/[a-f0-9]{40}/)) {
                setmap.disp_rev2 = rev2.substring(0, 8);
            }
            this.set(setmap);
        }
    });

    var IncomingLinksModel = exports.IncomingLinksModel = MasterPageModel.extend({
        urlRoot: '/api/inlinks/',
        _onChangePath: function(path) {
            IncomingLinksModel.__super__._onChangePath.apply(this, arguments);
            this.set('url_read', '/#/read/' + path);
        }
    });

    var WikiSearchModel = exports.WikiSearchModel = MasterPageModel.extend({
        urlRoot: '/api/search',
        title: function() {
            return 'Search';
        },
        url: function() {
            return this.urlRoot + '?q=' + this.get('query');
        }
    });

    var SpecialPagesModel = exports.SpecialPagesModel = MasterPageModel.extend({
        title: function() {
            return 'Special Pages';
        },
        initialize: function() {
            SpecialPagesModel.__super__.initialize.apply(this, arguments);
            this.set('sections', [
                {
                    title: "Wiki",
                    pages: [
                        {
                            title: "Recent Changes",
                            url: '/#/special/changes',
                            description: "See all changes in the wiki."
                        }
                    ]
                },
                {
                    title: "Page Lists",
                    pages: [
                        {
                            title: "Orphaned Pages",
                            url: '/#/special/list/orphans',
                            description: ("Lists pages in the wiki that have " +
                                          "no links to them.")
                        },
                        {
                            title: "Broken Redirects",
                            url: '/#/special/list/broken-redirects',
                            description: ("Lists pages that redirect to a " +
                                          "missing page.")
                        }
                    ]
                },
                {
                    title: "Users",
                    pages: [
                        {
                            title: "All Users",
                            url: '/#/special/users',
                            description: "A list of all registered users."
                        }
                    ]
                }
            ]);
        },
        _addFooterExtraUrls: function() {
        }
    });

    var SpecialPageModel = exports.SpecialPageModel = MasterPageModel.extend({
        initialize: function() {
            SpecialPageModel.__super__.initialize.apply(this, arguments);
        }
    });

    var SpecialChangesModel = exports.SpecialChangesModel = SpecialPageModel.extend({
        title: "Wiki History",
        initialize: function() {
            SpecialChangesModel.__super__.initialize.apply(this, arguments);
            this.on('change:history', this._onHistoryChanged, this);
        },
        url: function() {
            var url = '/api/site-history';
            if (this.get('after_rev'))
                url += '?rev=' + this.get('after_rev');
            return url;
        },
        _onHistoryChanged: function(model, history) {
            for (var i = 0; i < history.length; ++i) {
                var rev = history[i];
                rev.collapsed = (rev.pages.length > 3);
                for (var j = 0; j < rev.pages.length; ++j) {
                    var page = rev.pages[j];
                    switch (page.action) {
                        case 'edit':
                            page.action_label = 'edit';
                            break;
                        case 'add':
                            page.action_label = 'added';
                            break;
                        case 'delete':
                            page.action_label = 'deleted';
                            break;
                    }
                }
            }
            model.set('first_page', '/#/special/changes');
            if (history.length > 0) {
                var last_rev = history[0].rev_name;
                model.set('next_page', '/#/special/changes/' + last_rev);
            }
        }
    });

    var SpecialPageListModel = exports.SpecialPageListModel = SpecialPageModel.extend({
        title: function() { return this.titleMap[this.get('name')]; },
        url: function() { return '/api/' + this.get('name'); },
        initialize: function() {
            SpecialPageListModel.__super__.initialize.apply(this, arguments);
            var name = this.get('name');
            this.set({
                'title': this.titleMap[name],
                'message': this.messageMap[name],
                'aside': this.asideMap[name],
                'empty': this.emptyMap[name],
                'url_suffix': this.urlSuffix[name]
            });
        },
        titleMap: {
            'orphans': "Orphaned Pages",
            'broken-redirects': "Broken Redirects"
        },
        messageMap: {
            'orphans': ("Here is a list of pages that don't have any pages " +
                        "linking to them. This means user will only be able " +
                        "to find them by searching for them, or by getting " +
                        "a direct link."),
            'broken-redirects':
                        ("Here is a list of pages that redirect to a non-" +
                         "existing page.")
        },
        asideMap: {
            'orphans': ("The main page usually shows up here but that's " +
                        "OK since it's the page everyone sees first.")
        },
        emptyMap: {
            'orphans': "No orphaned pages!",
            'broken-redirects': "No broken redirects!"
        },
        urlSuffix: {
            'broken-redirects': '?no_redirect'
        }
    });

    return exports;
});

