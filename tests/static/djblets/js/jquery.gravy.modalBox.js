/*
 * Copyright 2008-2010 Christian Hammond.
 * Copyright 2010-2013 Beanbag, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to
 * deal in the Software without restriction, including without limitation the
 * rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
 * sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */
(function($) {


let modalBoxes = [];


/**
 * Handle focus changes throughout the document.
 *
 * If the focus has moved outside of the latest modalbox, focus will be reset
 * back to the inner portion of the box.
 *
 * Args:
 *     evt (Event):
 *         The focus event.
 */
function onDocumentFocusChanged(evt) {
    if (modalBoxes.length === 0) {
        return;
    }

    const modalBox = modalBoxes[modalBoxes.length - 1];

    if (!modalBox.box[0].contains(evt.target)) {
        evt.stopPropagation();
        modalBox.inner.focus();
    }
}


$.widget('ui.modalBox', {
    options: {
        buttons: [$('<input type="button">').val(gettext('Close'))],
        container: 'body',
        discardOnClose: true,
        fadeBackground: true,
        modalBoxButtonsClass: 'modalbox-buttons',
        modalBoxContentsClass: 'modalbox-contents',
        modalBoxTitleClass: 'modalbox-title',
        stretchX: false,
        stretchY: false,
        title: null
    },

    /**
     * Handle a keydown event.
     *
     * Args:
     *     e (KeyboardEvent):
     *         The event.
     */
    _onKeyDown: function(e) {
        e.stopPropagation();

        if (e.key === 'Escape') {
            this.element.trigger('close');
        }
    },

    _init: function() {
        var self = this;

        modalBoxes.push(this);

        this._onKeyDown = this._onKeyDown.bind(this);

        this._eventID = _.uniqueId('modalbox-');
        this._titleID = _.uniqueId('modalbox-title-');

        if (this.options.fadeBackground) {
            this.bgbox = $('<div>')
                .addClass('modalbox-bg')
                .attr('aria-hidden', 'true')
                .css({
                    'background-color': '#000',
                    opacity: 0
                })
                .move(0, 0, 'fixed')
                .width('100%')
                .height('100%')
                .on('keydown', this._onKeyDown)
                .appendTo(this.options.container);
        }

        this.box = $('<div>')
            .addClass('modalbox')
            .attr({
                'aria-labelledby': this._titleID,
                'aria-modal': 'true',
                role: 'dialog'
            })
            .move(0, 0, 'absolute')
            .on('keydown', this._onKeyDown);

        $('body').on('keydown', this._onKeyDown);

        if (this.options.boxID) {
            this.box.attr('id', this.options.boxID);
        }

        this.inner = $('<div>')
            .addClass('modalbox-inner')
            .attr('tabindex', '0')
            .css({
                height: '100%',
                position: 'relative',
                width: '100%'
            })
            .appendTo(this.box);

        if (this.options.title) {
            this.titleBox = $('<h1>')
                .attr('id', this._titleID)
                .addClass(this.options.modalBoxTitleClass)
                .text(this.options.title)
                .appendTo(this.inner);
        }

        this.element
            .addClass(this.options.modalBoxContentsClass)
            .appendTo(this.inner);

        this.observer = new MutationObserver(function() {
            self.resize();
        });
        this.observer.observe(this.element[0], {
            childList: true,
            subtree: true
        });

        this._buttons = $('<div>')
            .addClass(this.options.modalBoxButtonsClass)
            .click(function(e) {
                /* Check here so that buttons can call stopPropagation(). */
                if (!e.target.disabled &&
                    (e.target.tagName === 'INPUT' ||
                     e.target.tagName === 'BUTTON')) {
                    self.element.modalBox('destroy');
                }
            });

        $.each(this.options.buttons, function() {
            var $button = $(this),
                buttonEl = $button[0];

            if (buttonEl.tagName !== 'BUTTON' &&
                buttonEl.tagName !== 'INPUT' &&
                !$button.attr('role')) {
                $button.attr('role', 'button');
            }

            $button.appendTo(self._buttons);
        });

        this._buttons.appendTo(this.inner);

        if (this.options.fadeBackground && this.bgbox) {
            this.bgbox.fadeTo(350, 0.85);
        }

        this.box.appendTo(this.options.container);

        $(window).on('resize.' + this._eventID, function() {
            self.resize();
        });

        this.resize();
        this.inner.focus();

        /*
         * Listen for focus changes (at the capture phase) to make sure we
         * stay in the dialog.
         */
        if (modalBoxes.length === 1) {
            document.addEventListener('focus', onDocumentFocusChanged, true);
        }
    },

    destroy: function() {
        var self = this;

        if (!this.element.data('uiModalBox')) {
            return;
        }

        const modalBoxIndex = modalBoxes.indexOf(this);

        if (modalBoxIndex !== -1) {
            modalBoxes.splice(modalBoxIndex, 1);
        }

        this.element
            .removeData('uiModalBox')
            .off('resize.modalbox')
            .css('position', 'static');

        $(window).off('resize.' + this._eventID);

        if (modalBoxes.length === 0) {
            document.removeEventListener('focus', this._onDocumentFocusChanged,
                                         true);
        }

        this.observer.disconnect();

        if (this.options.fadeBackground) {
            this.bgbox.fadeOut(350, function() {
                self.bgbox.remove();
            });
        }

        if (!this.options.discardOnClose) {
            this.element.appendTo(this.options.container);
        }

        $('body').off('keydown', this._onKeyDown);

        this.box.remove();
    },

    buttons: function() {
        return this._buttons;
    },

    resize: function() {
        var marginHoriz = $('body').getExtents('m', 'lr'),
            marginVert = $('body').getExtents('m', 'tb'),
            winWidth = $(window).width() - marginHoriz,
            winHeight = $(window).height() - marginVert;

        if (this.options.stretchX) {
            this.box.width(winWidth -
                           this.box.getExtents('bmp', 'lr') -
                           marginHoriz);
        }

        if (this.options.stretchY) {
            this.box.height(winHeight -
                            this.box.getExtents('bmp', 'tb') -
                            marginVert);

            this.element.height(this._buttons.position().top -
                                this.element.position().top -
                                this.element.getExtents('mp', 'tb'));
        } else {
            this.box.height(this.element.position().top +
                            this.element.outerHeight(true) +
                            this._buttons.outerHeight(true));
        }

        this.box.move(Math.ceil((winWidth - this.box.outerWidth(true)) / 2),
                      Math.ceil((winHeight - this.box.outerHeight(true)) / 2),
                      'fixed');

        this.element.triggerHandler('resize');
    },
});

$.ui.modalBox.getter = 'buttons';


})(jQuery);

// vim: set et:
