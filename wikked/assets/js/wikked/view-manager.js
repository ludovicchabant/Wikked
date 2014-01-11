/**
 * An object responsible for opening, switching, and closing
 * down view.
 */
define([
        ],
    function() {

    var ViewManager = {
        _currentView: false,
        switchView: function(view, autoFetch) {
            if (this._currentView) {
                this._currentView.remove();
                this._currentView = false;
            }

            if (view) {
                this._currentView = view;
            }
        }
    };
});
