
define([
        'jquery',
        'underscore',
        ],
    function($, _) {

    var exports = {};

    // Main app method.
    var run = exports.run = function() {
        var nav = new NavigationView();
        window.wikkedNav = nav;
    };

    // Navigation menu view.
    var NavigationView = exports.NavigationView = function() {
        this.initialize.apply(this, arguments);
    };
    _.extend(NavigationView.prototype, {
        initialize: function() {
            // Hide the drop-down for the search results.
            this.searchPreviewList = $('#search-preview');
            this.searchPreviewList.hide();
            this.activeResultIndex = -1;

            // Cache some stuff for handling the menu.
            this.wikiMenu = $('#wiki-menu');
            this.wikiMenuAndWrapper = $.merge(this.wikiMenu, $('#app .wrapper'));
            this.isMenuActive = (this.wikiMenu.css('left') == '0px');
            this.isMenuActiveLocked = false;

            // Hookup events.
            this.listen("#wiki-menu-shortcut", 'click', '_onMenuShortcutClick');
            this.listen("#wiki-menu-pin", 'click', '_onMenuShortcutClick');
            this.listen("#wiki-menu-shortcut", 'mouseenter', '_onMenuShortcutHover');
            this.listen("#wiki-menu-shortcut", 'mouseleave', '_onMenuShortcutLeave');
            this.listen("#wiki-menu", 'mouseenter', '_onMenuHover');
            this.listen("#wiki-menu", 'mouseleave', '_onMenuLeave');
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
        _onMenuShortcutClick: function(e) {
            this.isMenuActive = !this.isMenuActive;
            var val = this.isMenuActive ? "1" : "0";
            document.cookie = (
                    "wiki-menu-active=" + val + "; " +
                    "path=/; expires=31 Dec 2100 UTC");
            this._toggleWikiMenuPin(this.isMenuActive);
        },
        _onMenuShortcutHover: function(e) {
            if (!this.isMenuActive && !this.isMenuActiveLocked)
                this._toggleWikiMenu(true);
        },
        _onMenuShortcutLeave: function(e) {
            if (!this.isMenuActive && !this.isMenuActiveLocked)
                this._toggleWikiMenu(false);
        },
        _onMenuHover: function(e) {
            if (!this.isMenuActive && !this.isMenuActiveLocked)
                this._toggleWikiMenu(true);
        },
        _onMenuLeave: function(e) {
            if (!this.isMenuActive && !this.isMenuActiveLocked)
                this._toggleWikiMenu(false);
        },
        _toggleWikiMenu: function(onOff) {
            if (onOff) {
                this.wikiMenuAndWrapper.toggleClass('wiki-menu-inactive', false);
                this.wikiMenuAndWrapper.toggleClass('wiki-menu-active', true);
            } else {
                this.wikiMenuAndWrapper.toggleClass('wiki-menu-active', false);
                this.wikiMenuAndWrapper.toggleClass('wiki-menu-inactive', true);
            }
        },
        _toggleWikiMenuPin: function(onOff) {
            $('#wiki-menu-pin').toggleClass('wiki-menu-pin-active', onOff);
        },
        _searchQueryFocused: function(e) {
            this.isMenuActiveLocked = true;
            this.wikiMenu.toggleClass('wiki-menu-ext', true);
        },
        _searchQueryBlurred: function(e) {
            $(e.currentTarget).val('').trigger('input');
            this.wikiMenu.toggleClass('wiki-menu-ext', false);
            this.isMenuActiveLocked = false;
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

    return exports;
});

