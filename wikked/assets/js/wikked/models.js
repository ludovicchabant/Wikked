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
        idAttribute: 'path',
        defaults: function() {
            return {
                path: "",
                action: "read",
                user: false
            };
        },
        initialize: function() {
            this.on('change:path', function(model, path) {
                model._onChangePath(path);
            });
            this._onChangePath(this.get('path'));
            this.on('change:auth', function(model, auth) {
                model._onChangeAuth(auth);
            });
            this._onChangeAuth(this.get('auth'));
            return this;
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
                    this._flushPendingQuery();
                })
                .fail(function() {
                    $model._isSearching = false;
                    this._flushPendingQuery();
                });
        },
        doSearch: function(form) {
            this.navigate('/search/' + $(form.q).val(), { trigger: true });
        },
        doNewPage: function(form) {
            this.navigate('/create/', { trigger: true });
        },
        _onChangePath: function(path) {
            this.set({
                url_home: '/',
                url_read: '/#/read/' + path,
                url_edit: '/#/edit/' + path,
                url_hist: '/#/changes/' + path,
                url_search: '/search'
            });
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
        _onChangeAuth: function(auth) {
            if (auth) {
                this.set({
                    url_login: false,
                    url_logout: '/#/logout',
                    username: auth.username
                });
            } else {
                this.set({
                    url_login: '/#/login',
                    url_logout: false,
                    username: false
                });
            }
        }
    });

    var FooterModel = exports.FooterModel = Backbone.Model.extend({
        defaults: function() {
            return {
                url_extras: [
                    { name: 'Special Pages', url: '/#/special', icon: 'dashboard' }
                ]
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
        _onChangePath: function(path) {
        },
        _onChangeText: function(text) {
            this.set('content', new Handlebars.SafeString(text));
        }
    });

    var PageStateModel = exports.PageStateModel = PageModel.extend({
        urlRoot: '/api/state/',
        _onChangePath: function(path) {
            PageStateModel.__super__._onChangePath.apply(this, arguments);
            this.set('url_edit', '/#/edit/' + path);
        }
    });

    var MasterPageModel = exports.MasterPageModel = PageModel.extend({
        initialize: function() {
            this.nav = new NavigationModel({ id: this.id });
            this.footer = new FooterModel();
            MasterPageModel.__super__.initialize.apply(this, arguments);
            this.on('change:auth', function(model, auth) {
                model._onChangeAuth(auth);
            });
            this.on('error', this._onError, this);
            if (this.action !== undefined) {
                this.nav.set('action', this.action);
                this.footer.set('action', this.action);
            }
            return this;
        },
        _onAppSet: function(app) {
            this.nav.app = app;
            this.footer.app = app;
        },
        _onChangePath: function(path) {
            MasterPageModel.__super__._onChangePath.apply(this, arguments);
            this.nav.set('path', path);
        },
        _onChangeAuth: function(auth) {
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
        action: 'read',
        initialize: function() {
            PageReadModel.__super__.initialize.apply(this, arguments);
            this.on('change', this._onChange, this);

            // Add extra links to the footer.
            var model = this;
            this.footer.addExtraUrl(
                'Pages Linking Here',
                function() { return '/#/inlinks/' + model.id; },
                1,
                'link');
            this.footer.addExtraUrl(
                'JSON',
                function() { return '/api/read/' + model.id; },
                -1,
                'cog');
        },
        checkStatePath: function() {
            return this.get('path');
        },
        _onChange: function() {
            if (this.getMeta('redirect')) {
                // Handle redirects.
                var newPath = this.getMeta('redirect').replace(/^\//, "");
                if (this.get('no_redirect')) {
                    this.set({ 'redirects_to': newPath }, { 'silent': true });
                } else {
                    var oldPath = this.get('path');
                    this.set({
                        'path': newPath,
                        'redirected_from': oldPath
                    }, {
                        'silent': true
                    });
                    this.fetch();
                    this.navigate('/read/' + newPath, { replace: true, trigger: false });
                }
            }
        }
    });

    var PageSourceModel = exports.PageSourceModel = MasterPageModel.extend({
        urlRoot: '/api/raw/',
        action: 'source'
    });

    var PageEditModel = exports.PageEditModel = MasterPageModel.extend({
        action: 'edit',
        urlRoot: '/api/edit/',
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
        _onChangePath: function(path) {
            PageEditModel.__super__._onChangePath.apply(this, arguments);
            this.set('url_read', this._getReadPath(path));
        },
        _onEditSuccess: function() {
            this.navigate('/read/' + this.get('path'), { trigger: true });
        },
        _getReadPath: function(path) {
            return '/#/read/' + path;
        }
    });

    var PageHistoryModel = exports.PageHistoryModel = MasterPageModel.extend({
        urlRoot: '/api/history/',
        action: 'history',
        initialize: function() {
            PageHistoryModel.__super__.initialize.apply(this, arguments);
            var model = this;
            this.footer.addExtraUrl(
                'JSON',
                function() { return '/api/history/' + model.id; },
                -1,
                'road');
        },
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
        action: 'revision',
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
            this.on('change:rev', function(model, rev) {
                model._onChangeRev(rev);
            });
            this._onChangeRev(this.get('rev'));
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
        _onChangeRev: function(rev) {
            var setmap = { disp_rev: rev };
            if (rev.match(/[a-f0-9]{40}/)) {
                setmap.disp_rev = rev.substring(0, 8);
            }
            this.set(setmap);
        }
    });

    var PageDiffModel = exports.PageDiffModel = MasterPageModel.extend({
        action: 'diff',
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
            this.on('change:rev1', function(model, rev1) {
                model._onChangeRev1(rev1);
            });
            this.on('change:rev2', function(model, rev2) {
                model._onChangeRev2(rev2);
            });
            this._onChangeRev1(this.get('rev1'));
            this._onChangeRev2(this.get('rev2'));
            return this;
        },
        _onChangeRev1: function(rev1) {
            var setmap = { disp_rev1: rev1 };
            if (rev1 !== undefined && rev1.match(/[a-f0-9]{40}/)) {
                setmap.disp_rev1 = rev1.substring(0, 8);
            }
            this.set(setmap);
        },
        _onChangeRev2: function(rev2) {
            var setmap = { disp_rev2:  rev2 };
            if (rev2 !== undefined && rev2.match(/[a-f0-9]{40}/)) {
                setmap.disp_rev2 = rev2.substring(0, 8);
            }
            this.set(setmap);
        }
    });

    var IncomingLinksModel = exports.IncomingLinksModel = MasterPageModel.extend({
        urlRoot: '/api/inlinks/',
        action: 'inlinks',
        _onChangePath: function(path) {
            IncomingLinksModel.__super__._onChangePath.apply(this, arguments);
            this.set('url_read', '/#/read/' + path);
        }
    });

    var WikiSearchModel = exports.WikiSearchModel = MasterPageModel.extend({
        urlRoot: '/api/search',
        action: 'search',
        title: function() {
            return 'Search';
        },
        url: function() {
            return this.urlRoot + '?q=' + this.get('query');
        }
    });

    var SpecialPagesModel = exports.SpecialPagesModel = MasterPageModel.extend({
        action: 'special',
        title: function() {
            return 'Special Pages';
        },
        initialize: function() {
            SpecialPagesModel.__super__.initialize.apply(this, arguments);
            this.footer.clearExtraUrls();
        }
    });

    var SpecialPageModel = exports.SpecialPageModel = MasterPageModel.extend({
        action: 'special',
        initialize: function() {
            SpecialPageModel.__super__.initialize.apply(this, arguments);
            this.footer.clearExtraUrls();
        }
    });

    var SpecialChangesModel = exports.SpecialChangesModel = SpecialPageModel.extend({
        title: "Wiki History",
        url: '/api/history'
    });

    var SpecialOrphansModel = exports.SpecialOrphansModel = SpecialPageModel.extend({
        title: "Orphaned Pages",
        url: '/api/orphans'
    });

    return exports;
});

