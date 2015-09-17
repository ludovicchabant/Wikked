/**
 * Wikked views.
 */
define([
        'jquery',
        'underscore'
        ],
    function($, _) {

    var exports = {};

    // JQuery feature for watching size changes in a DOM element.
    /*jQuery.fn.watch = function(id, fn) {
        return this.each(function() {
            var self = this;
            var oldVal = self[id];
            $(self).data(
                'watch_timer',
                setInterval(
                    function() {
                        if (self[id] !== oldVal) {
                            fn.call(self, id, oldVal, self[id]);
                            oldVal = self[id];
                        }
                    },
                    100
                )
            );
        });
    };
    jQuery.fn.unwatch = function(id) {
        return this.each(function() {
            clearInterval($(this).data('watch_timer'));
        });
    };*/

    // Override JQuery-validation plugin's way of highlighting errors
    // with something that works with Bootstrap.
    /*$.validator.setDefaults({
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
    });*/

    /*var PageEditView = exports.PageEditView = MasterPageView.extend({
        defaultTemplateSource: tplEditPage,
        dispose: function() {
            PageEditView.__super__.dispose.apply(this, arguments);
        },
        renderCallback: function() {
            PageEditView.__super__.renderCallback.apply(this, arguments);
            if (this.isError) {
                return;
            }

            // Initialize the preview.
            this.inputSection = $('.editing-input');
            this.inputCtrl = $('#editing-input-area');
            this.previewSection = $('.editing-preview');
            this.previewSection.hide();
            this.previewButtonLabel = $('.editing-preview-button-label');
            this.errorSection = $('.editing-error');
            this.errorSection.hide();

            // Start validation on the form.
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
        },
        events: {
            "mousedown #editing-input-grip": "_inputGripMouseDown",
            "click #editing-preview-button": "_togglePreview",
            "click #editing-cancel-button": "_cancelEdit",
            "submit #page-edit": "_submitEditedPage"
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
                this.inputSection.show();
                this.previewSection.hide();
                this.previewButtonLabel.html("Preview");
                return;
            }

            // Get the server to compute the preview text, hide the textbox,
            // show the rendered text.
            var $view = this;
            var previewData = {
                url: this.model.get('path'),
                text: this.inputCtrl.val()
            };
            $.post('/api/preview', previewData)
                .success(function(data) {
                    var el = $view.previewSection;
                    el.html(data.text);
                    processWikiLinks(el);
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
        },
        _submitEditedPage: function(e) {
            // Make the model submit the form.
            e.preventDefault();
            this.model.doEdit(e.currentTarget);
            return false;
        },
        _cancelEdit: function(e) {
            e.preventDefault();
            this.model.doCancel();
            return false;
        },
        titleFormat: function(title) {
            return 'Editing: ' + title;
        }
    });*/

    /*var SpecialChangesView = exports.SpecialChangesView = SpecialMasterPageView.extend({
        defaultTemplateSource: tplSpecialChanges,
        renderCallback: function() {
            SpecialChangesView.__super__.renderCallback.apply(this, arguments);
            if (this.isError) {
                return;
            }

            this.$('.wiki-history .wiki-history-entry-details').hide();
            this.$('.wiki-history .wiki-history-entry-collapser').click(function(e) {
                var btn = $(this);
                index = btn.attr('data-index');
                var tgt = $('.wiki-history .wiki-history-entry-details-' + index);
                tgt.toggle();
                if (tgt.is(':visible')) {
                    $('.fa', btn).removeClass('fa-chevron-down');
                    $('.fa', btn).addClass('fa-chevron-up');
                    $('small', btn).html('Hide');
                } else {
                    $('.fa', btn).removeClass('fa-chevron-up');
                    $('.fa', btn).addClass('fa-chevron-down');
                    $('small', btn).html('Show');
                }
                e.preventDefault();
            });
        }
    });*/

    return exports;
});

