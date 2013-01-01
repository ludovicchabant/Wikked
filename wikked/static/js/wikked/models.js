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
            this.app.navigate('/search/' + $(form.q).val(), { trigger: true });
        },
        _onChangePath: function(path) {
            this.set('url_home', '/#/read/main-page');
            this.set('url_read', '/#/read/' + path);
            this.set('url_edit', '/#/edit/' + path);
            this.set('url_hist', '/#/changes/' + path);
            this.set('url_search', '/search');
        },
        _isSearching: false,
        _onChangeAuth: function(auth) {
            if (auth) {
                this.set('url_login', false);
                this.set('url_logout', '/#/logout');
                this.set('username', auth.username);
            } else {
                this.set('url_login', '/#/login');
                this.set('url_logout', false);
                this.set('username', false);
            }
        }
    });

    var FooterModel = exports.FooterModel = Backbone.Model.extend({
        defaults: function() {
            return {
                url_extras: [
                    { name: 'Home', url: '/' },
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
                    $model.app.navigate('/', { trigger: true });
                })
                .error(function() {
                    alert("Error while logging in...");
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
        urlRoot: '/api/state/'
    });
    
    var MasterPageModel = exports.MasterPageModel = PageModel.extend({
        initialize: function() {
            this.nav = new NavigationModel({ id: this.id });
            this.footer = new FooterModel();
            MasterPageModel.__super__.initialize.apply(this, arguments);
            this.on('change:auth', function(model, auth) {
                model._onChangeAuth(auth);
            });
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
        }
    });

    var PageReadModel = exports.PageReadModel = MasterPageModel.extend({
        urlRoot: '/api/read/',
        action: 'read',
        _onChangePath: function(path) {
            PageReadModel.__super__._onChangePath.apply(this, arguments);
            this.footer.addExtraUrl('Pages Linking Here', '/#/inlinks/' + path, 1);
            this.footer.addExtraUrl('JSON', '/api/read/' + path);
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
            $.post('/api/edit/' + path, $(form).serialize())
                .success(function(data) {
                    $model.app.navigate('/read/' + path, { trigger: true });
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
            this.app.navigate('/diff/r/' + this.get('path') + '/' + rev1 + '/' + rev2, { trigger: true });
        },
        _onChangePath: function(path) {
            PageHistoryModel.__super__._onChangePath.apply(this, arguments);
            this.set('url_rev', '/#/revision/' + path);
            this.set('url_diffc', '/#/diff/c/' + path);
            this.set('url_diffr', '/#/diff/r/' + path);
        }
    });

    var PageRevisionModel = exports.PageRevisionModel = MasterPageModel.extend({
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

    var PageDiffModel = exports.PageDiffModel = MasterPageModel.extend({
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
        urlRoot: '/api/special',
        idAttribute: 'page',
        initialize: function() {
            GenericSpecialPageModel.__super__.initialize.apply(this, arguments);
            this.footer.clearExtraUrls();
        }
    });

    return exports;
});

