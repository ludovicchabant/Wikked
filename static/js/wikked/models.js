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
                path: "main-page",
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
                return;
            }
            this._isSearching = true;
            var $model = this;
            $.getJSON('/api/search', { q: query })
                .success(function (data) {
                    $model._isSearching = false;
                    callback(data);
                })
                .error(function() {
                    $model._isSearching = false;
                });
        },
        doSearch: function(form) {
            this.navigate('/search/' + $(form.q).val(), { trigger: true });
        },
        _onChangePath: function(path) {
            this.set({
                url_home: '/#/read/main-page',
                url_read: '/#/read/' + path,
                url_edit: '/#/edit/' + path,
                url_hist: '/#/changes/' + path,
                url_search: '/search'
            });
        },
        _isSearching: false,
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
                    { name: 'Home', url: '/#/' },
                    { name: 'Special Pages', url: '/#/special' }
                ]
            };
        },
        clearExtraUrls: function() {
            this.get('url_extras').length = 0;
        },
        addExtraUrl: function(name, url, index) {
            if (index === undefined) {
                this.get('url_extras').push({ name: name, url: url });
            } else {
                this.get('url_extras').splice(index, 0, { name: name, url: url });
            }
        }
    });

    var LoginModel = exports.LoginModel = Backbone.Model.extend({
        setApp: function(app) {
            this.app = app;
        },
        doLogin: function(form) {
            var $model = this;
            $.post('/api/user/login', $(form).serialize())
                .success(function() {
                    $model.navigate('/', { trigger: true });
                })
                .error(function() {
                    $model.set('has_error', true);
                });
        }
    });

    var PageModel = exports.PageModel = Backbone.Model.extend({
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
            this.footer.addExtraUrl('Pages Linking Here', function() { return '/#/inlinks/' + model.id; }, 1);
            this.footer.addExtraUrl('JSON', function() { return '/api/read/' + model.id; });
        },
        _onChange: function() {
            if (this.getMeta('redirect') && 
                !this.get('no_redirect') &&
                !this.get('redirected_from')) {
                // Handle redirects.
                var oldPath = this.get('path');
                this.set({
                    'path': this.getMeta('redirect'),
                    'redirected_from': oldPath
                });
                this.fetch();
                this.navigate('/read/' + this.getMeta('redirect'), { replace: true, trigger: false });
            }
        }
    });

    var PageSourceModel = exports.PageSourceModel = MasterPageModel.extend({
        urlRoot: '/api/raw/',
        action: 'source'
    });

    var PageEditModel = exports.PageEditModel = MasterPageModel.extend({
        urlRoot: '/api/edit/',
        action: 'edit',
        doEdit: function(form) {
            var $model = this;
            var path = this.get('path');
            this.navigate('/read/' + path, { trigger: true });
            $.post('/api/edit/' + path, $(form).serialize())
                .success(function(data) {
                    $model.navigate('/read/' + path, { trigger: true });
                })
                .error(function() {
                    alert('Error saving page...');
                });
        }
    });

    var PageHistoryModel = exports.PageHistoryModel = MasterPageModel.extend({
        urlRoot: '/api/history/',
        action: 'history',
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
                path: "main-page",
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
                path: "main-page",
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
        action: 'inlinks'
    });

    var WikiSearchModel = exports.WikiSearchModel = MasterPageModel.extend({
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

    var GenericSpecialPageModel = exports.GenericSpecialPageModel = MasterPageModel.extend({
        action: 'special',
        initialize: function() {
            GenericSpecialPageModel.__super__.initialize.apply(this, arguments);
            this.footer.clearExtraUrls();
        },
        titleMap: {
            orphans: 'Orphaned Pages',
            changes: 'Wiki History'
        },
        title: function() {
            var key = this.get('page');
            if (key in this.titleMap) {
                return this.titleMap[key];
            }
            return 'Unknown';
        },
        urlMap: {
            orphans: '/api/orphans',
            changes: '/api/history'
        },
        url: function() {
            var key = this.get('page');
            if (key in this.urlMap) {
                return this.urlMap[key];
            }
            return false;
        }
    });

    return exports;
});

