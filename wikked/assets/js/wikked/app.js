var _ = require('underscore');
var $ = require('jquery');


// Navigation menu view.
var NavigationView = function() {
    this.initialize.apply(this, arguments);
};
_.extend(NavigationView.prototype, {
    initialize: function() {
        // Hide the drop-down for the search results.
        this.searchPreviewList = $('#search-preview');
        this.searchPreviewList.hide();
        this.activeResultIndex = -1;

        // Cache some stuff for handling the menu.
        this.wikiBody = $('body');
        this.wikiApp = $('#app');
        this.wikiMenu = $('#wiki-menu');
        this.wikiMenuLock = $('#wiki-menu-lock');
        this.isMenuActive = (this.wikiMenu.css('left') == '0px');
        this.isMenuLocked = (this.wikiApp.hasClass('wiki-menu-locked'));

        // Hookup events.
        this.listen("#wiki-menu-shortcut", 'click', '_onMenuShortcutClick');
        this.listen("#wiki-menu-lock", 'click', '_onMenuLockClick');
        this.listen("#wiki-menu-lock", 'mouseenter', '_onMenuLockHoverLeave');
        this.listen("#wiki-menu-lock", 'mouseleave', '_onMenuLockHoverLeave');
        this.listen("#app .wrapper", 'click', '_onBackgroundClick');

        this.listen("#search-query", 'focus', '_searchQueryFocused');
        this.listen("#search-query", 'input', '_previewSearch');
        this.listen("#search-query", 'keyup', '_searchQueryChanged');
        this.listen("#search-query", 'blur', '_searchQueryBlurred');
        this.listen("#search", 'submit', '_submitSearch');
    },
    listen: function(sel, evt, callback) {
        var _t = this;
        $(sel).on(evt, function(e) {
            _t[callback](e);
        });
    },

    _toggleWikiMenu: function() {
        this.isMenuActive = !this.isMenuActive;
        if (this.isMenuActive) {
            this.wikiApp.toggleClass('wiki-menu-inactive', false);
            this.wikiApp.toggleClass('wiki-menu-active', true);
        } else {
            this.wikiApp.toggleClass('wiki-menu-active', false);
            this.wikiApp.toggleClass('wiki-menu-inactive', true);
        }
    },
    _onMenuShortcutClick: function(e) {
        this._toggleWikiMenu();
    },

    _lockUnlockWikiMenu: function() {
        var val = this.isMenuLocked ? "0" : "1";
        document.cookie = (
                "wiki-nav-locked=" + val + "; " +
                "path=/; expires=31 Dec 2100 UTC");
        this.wikiApp.toggleClass('wiki-menu-locked');
        this.isMenuLocked = !this.isMenuLocked;
    },
    _onMenuLockClick: function(e) {
        this._lockUnlockWikiMenu();
    },

    _onMenuLockHoverLeave: function(e) {
        this.wikiMenuLock.toggleClass('fa-lock');
        this.wikiMenuLock.toggleClass('fa-unlock');
    },

    _onBackgroundClick: function(e) {
        if (!this.isMenuLocked && this.isMenuActive)
            this._toggleWikiMenu();
    },

    _searchQueryFocused: function(e) {
        this.wikiMenu.toggleClass('wiki-menu-ext', true);
        this.wikiBody.toggleClass('wiki-search-underlayer', true);
    },
    _searchQueryBlurred: function(e) {
        this.wikiBody.toggleClass('wiki-search-underlayer', false);
        this.wikiMenu.toggleClass('wiki-menu-ext', false);
        if (this.searchPreviewList.is(':visible'))
            this.searchPreviewList.slideUp(200);
        if ($(document.activeElement).parents('#wiki-menu').length === 0)
            this._onMenuLeave(e);
    },
    _submitSearch: function(e) {
        if (this.activeResultIndex >= 0) {
            var entries = this.searchPreviewList.children();
            var choice = $('a', entries[this.activeResultIndex]);
            var url = choice.attr('href') + "?no_redirect";
            window.location.href = url;
            e.preventDefault();
            return false;
        }
        return true;
    },
    _previewSearch: function(e) {
        var query = $(e.currentTarget).val();
        if (query && query.length >= 1) {
            var $view = this;
            this._doPreviewSearch(query, function(data) {
                var resultStr = '';
                for (var i = 0; i < data.hits.length; ++i) {
                    var hitUrl = data.hits[i].url.replace(/^\//, '');
                    resultStr += '<li>' +
                        '<a href="/read/' + hitUrl + '">' +
                        data.hits[i].title +
                        '</a>' +
                        '</li>';
                }
                $view.searchPreviewList.html(resultStr);
                if (!$view.searchPreviewList.is(':visible'))
                    $view.searchPreviewList.slideDown(200);
            });
        } else if(!query || query.length === 0) {
            this.searchPreviewList.slideUp(200);
        }
    },
    _isSearching: false,
    _pendingQuery: null,
    _pendingCallback: null,
    _doPreviewSearch: function(query, callback) {
        if (this._isSearching) {
            this._pendingQuery = query;
            this._pendingCallback = callback;
            return;
        }
        this._isSearching = true;
        var $view = this;
        $.getJSON('/api/searchpreview', { q: query })
            .done(function (data) {
                $view._isSearching = false;
                callback(data);
                $view._flushPendingQuery();
            })
            .fail(function() {
                $view._isSearching = false;
                $view._flushPendingQuery();
            });
    },
    _flushPendingQuery: function() {
        if (this._pendingQuery && this._pendingCallback) {
            var q = this._pendingQuery;
            var c = this._pendingCallback;
            this._pendingQuery = null;
            this._pendingCallback = null;
            this._doPreviewSearch(q, c);
        }
    },
    _searchQueryChanged: function(e) {
        if (e.keyCode == 27) {
            // Clear search on `Esc`.
            $(e.currentTarget).val('').trigger('input');
        } else if (e.keyCode == 38) {
            // Up arrow.
            e.preventDefault();
            if (this.activeResultIndex >= 0) {
                this.activeResultIndex--;
                this._updateActiveResult();
            }
        } else if (e.keyCode == 40) {
            // Down arrow.
            e.preventDefault();
            if (this.activeResultIndex < 
                    this.searchPreviewList.children().length - 1) {
                this.activeResultIndex++;
                this._updateActiveResult();
            }
        }
    },
    _updateActiveResult: function() {
        var entries = this.searchPreviewList.children();
        entries.toggleClass('search-result-hover', false);
        if (this.activeResultIndex >= 0)
            $(entries[this.activeResultIndex]).toggleClass('search-result-hover', true);
    }
});

module.exports = function runapp() {
    var nav = new NavigationView();
    window.wikkedNav = nav;
};

