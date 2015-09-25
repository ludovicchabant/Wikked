
define([
        'jquery',
        'jquery_validate',
        'underscore',
        ],
    function($, JQueryValidate, _) {

    var exports = {};

    // Edit initialization.
    var run = exports.run = function() {
        var editView = new EditPageView();
        window.wikkedEditView = editView;
    };

    // Override JQuery-validation plugin's way of highlighting errors
    // with something that works with Bootstrap.
    $.validator.setDefaults({
        highlight: function(element) {
            $(element).closest('.form-group')
                .addClass('has-error')
                .removeClass('has-success');
        },
        unhighlight: function(element) {
            $(element).closest('.form-group')
                .removeClass('has-error')
                .addClass('has-success');
        },
        errorElement: 'span',
        errorClass: 'help-block',
        errorPlacement: function(error, element) {
            if(element.parent('.input-group').length) {
                error.insertAfter(element.parent());
            } else {
                error.insertAfter(element);
            }
        }
    });

    // Edit page functionality.
    var EditPageView = exports.EditPageView = function() {
        this.initialize.apply(this, arguments);
    };
    _.extend(EditPageView.prototype, {
        initialize: function() {
            this.inputSection = $('.editing-input');
            this.inputCtrl = $('#editing-input-area');

            this.previewSection = $('.editing-preview');
            this.previewButtonLabel = $('.editing-preview-button-label');
            this.previewSection.hide();

            this.errorSection = $('.editing-error');
            this.errorSection.hide();

            $('#page-edit').validate({
                rules: {
                    title: {
                        required: true,
                        remote: {
                            url: '/api/validate/newpage',
                            type: 'post'
                        }
                    }
                }
            });

            this.listen('#editing-input-grip', 'mousedown', 
                        '_inputGripMouseDown');
            this.listen('#editing-preview-button', 'click', '_togglePreview');
        },
        listen: function(sel, evt, callback) {
            var _t = this;
            $(sel).on(evt, function(e) {
                _t[callback](e);
            });
        },
        _inputGripMouseDown: function(e) {
            // Input area resizing with the grip.
            var $view = this;
            var last_pageY = e.pageY;
            $('body')
                .on('mousemove.wikked.editor_resize', function(e) {
                    var ctrl = $view.inputCtrl;
                    ctrl.height(ctrl.height() + e.pageY - last_pageY);
                    last_pageY = e.pageY;
                })
                .on('mouseup.wikked.editor_resize mouseleave.wikked.editor_resize', function(e) {
                    $('body').off('.wikked.editor_resize');
                });
        },
        _togglePreview: function(e) {
            e.preventDefault();

            if (this.previewSection.is(':visible')) {
                // Hide the preview, restore the textbox.
                this.inputCtrl.height(Math.max(
                            this.inputCtrl.height(),
                            this.previewSection.height() - 12));
                this.inputSection.show();
                this.previewSection.hide();
                this.previewButtonLabel.html("Preview");
                return false;
            }

            // Get the server to compute the preview text, hide the textbox,
            // show the rendered text.
            var $view = this;
            var previewBtn = $('#editing-preview-button');
            var previewData = {
                url: previewBtn.attr('data-wiki-url'),
                text: this.inputCtrl.val()
            };
            this.previewSection.html("<p>Loading...</p>");
            this.previewSection.height(this.inputSection.height());
            this.previewSection.show();
            this.inputSection.hide();
            $.post('/api/preview', previewData)
                .success(function(data) {
                    var el = $view.previewSection;
                    el.height('auto');
                    el.html(data.text);
                    el.height(Math.max(
                            el.height(),
                            $view.inputSection.height()));
                    el.show();
                    $view.inputSection.hide();
                    $view.previewButtonLabel.html("Edit");
                    $view.errorSection.hide();
                })
                .error(function() {
                    $('.editing-error-message').html("Error running preview.");
                    $view.errorSection.show();
                });
            return false;
        }
    });

    return exports;
});

