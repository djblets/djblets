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


$.widget("ui.inlineEditor", {
    options: {
        cls: "",
        editIconPath: null,
        editIconClass: null,
        enabled: true,
        extraHeight: 100,
        fadeSpeedMS: 200,
        focusOnOpen: true,
        forceOpen: false,
        formatResult: null,
        hasRawValue: false,
        matchHeight: true,
        multiline: false,
        notifyUnchangedCompletion: false,
        promptOnCancel: true,
        rawValue: null,
        showButtons: true,
        showEditIcon: true,
        startOpen: false,
        stripTags: false,
        useEditIconOnly: false
    },

    _create: function() {
        /* Constants */
        var self = this;

        /* State */
        this._initialValue = null;
        this._editing = false;
        this._dirty = false;

        /* Elements */
        this._form = $("<form/>")
            .addClass("inline-editor-form " + this.options.cls)
            .css("display", "inline")
            .insertBefore(this.element)
            .hide();

        if (this.options.multiline) {
            this._field = $("<textarea/>")
                .appendTo(this._form)
                .autoSizeTextArea();
        } else {
            this._field = $('<input type="text"/>')
                .appendTo(this._form);
        }

        this._field
            .keydown(function(e) {
                e.stopPropagation();

                var keyCode = e.keyCode ? e.keyCode :
                                e.charCode ? e.charCode : e.which;

                switch (keyCode) {
                    case $.ui.keyCode.ENTER:
                        /* Enter */
                        if (!self.options.forceOpen &&
                            (!self.options.multiline || e.ctrlKey)) {
                            self.submit();
                        }

                        if (!self.options.multiline) {
                            e.preventDefault();
                        }
                        break;

                    case $.ui.keyCode.ESCAPE:
                        /* Escape */
                        if (!self.options.forceOpen) {
                            self.cancel();
                        }
                        break;

                    case 83:
                    case 115:
                        /* s or S */
                        if (e.ctrlKey) {
                            self.save();
                            return false;
                        }
                        break;

                    default:
                        break;
                }
            })
            .keypress(function(e) {
                e.stopPropagation();
            })
            .keyup(function(e) {
                self._updateDirtyState();
            });

        this._buttons = null;

        if (this.options.showButtons) {
            this._buttons = $("<div/>")
                .addClass("buttons")
                .appendTo(this._form);

            if (!this.options.multiline) {
                this._buttons.css("display", "inline");
            }

            /*
             * Hide it after we've set the display, so it'll know what to
             * restore to when we call show().
             */
            this._buttons.hide();

            var saveButton =
                $('<input type="button"/>')
                .val("OK")
                .addClass("save")
                .appendTo(this._buttons)
                .click(function() { self.submit(); });

            var cancelButton =
                $('<input type="button"/>')
                .val("Cancel")
                .addClass("cancel")
                .appendTo(this._buttons)
                .click(function() { self.cancel(); });
        }

        this._editIcon = null;

        if (this.options.showEditIcon) {
            this._editIcon =
                $("<a/>")
                .attr('href', '#')
                .attr("role", "button")
                .attr("aria-label", "Edit this field")
                .addClass("editicon")
                .click(function() {
                    self.startEdit();
                    return false;
                });

            if (this.options.editIconPath) {
                this._editIcon.append(
                    '<img src="' + this.options.editIconPath + '"/>');
            } else if (this.options.editIconClass) {
                this._editIcon.append(
                    '<div class="' + this.options.editIconClass + '"></div>');
            }

            if (this.options.showRequiredFlag) {
                this._editIcon.append(
                    $("<span/>")
                        .attr("aria-label", "This field is required")
                        .addClass("required-flag")
                        .text("*"));
            }

            if (this.options.multiline) {
                this._editIcon.appendTo(
                    $("label[for=" + this.element[0].id + "]"));
            } else {
                this._editIcon.insertAfter(this.element);
            }
        }

        if (!this.options.useEditIconOnly) {
            /*
             * Check if the mouse was dragged, so the editor isn't opened when
             * text is selected.
             */
            var isDragging = true;

            this.element
                .mousedown(function() {
                    isDragging = false;
                    $(this).one("mousemove", function() {
                        isDragging = true;
                    });
                })
                .mouseup(function() {
                    $(this).unbind("mousemove");
                    var wasDragging = isDragging;
                    isDragging = true;
                    if (!wasDragging) {
                        self.startEdit();
                    }

                    return false;
                });
        }

        $(window).resize(function() {
            self._fitWidthToParent();
        });

        if (this.options.forceOpen || this.options.startOpen) {
            self.startEdit(true);
        }

        if (this.options.enabled) {
            self.enable();
        } else {
            self.disable();
        }
    },

    /*
     * Enables use of the inline editor.
     */
    enable: function() {
        if (this._editing) {
            this.showEditor();
        }

        if (this._editIcon) {
            this._editIcon.css('visibility', 'visible');
        }

        this.options.enabled = true;
    },

    /*
     * Disables use of the inline editor.
     */
    disable: function() {
        if (this._editing) {
            this.hideEditor();
        }

        if (this._editIcon) {
            this._editIcon.css('visibility', 'hide');
        }

        this.options.enabled = false;
    },

    /*
     * Puts the editor into edit mode.
     */
    startEdit: function(preventAnimation) {
        var value;

        if (this._editing || !this.options.enabled) {
            return;
        }

        if (this.options.hasRawValue) {
            this._initialValue = this.options.rawValue;
            value = this._initialValue;
        } else {
            this._initialValue = this.element.text();
            value = this._normalizeText(this._initialValue).htmlDecode();
        }
        this._editing = true;

        this._field.val(value);

        this.showEditor(preventAnimation);
        this.element.triggerHandler("beginEdit");
    },

    /*
     * Saves the contents of the editor.
     */
    save: function() {
        var value = this.value(),
            encodedValue = value.htmlEncode(),
            initialValue = this._initialValue;

        if (this._dirty) {
            this.element.html($.isFunction(this.options.formatResult)
                              ? this.options.formatResult(encodedValue)
                              : encodedValue);
            this._initialValue = this.element.text();
        }

        if (this._dirty || this.options.notifyUnchangedCompletion) {
            this.element.triggerHandler("complete",
                                        [value, initialValue]);

            if (this.options.hasRawValue) {
                this.options.rawValue = value;
            }
        } else {
            this.element.triggerHandler("cancel", [this._initialValue]);
        }
    },

    submit: function() {
        // hideEditor() resets the _dirty flag, thus we need to do save() first.
        this.save();
        this.hideEditor();
    },

    cancel: function(force) {
        if (!force && this.options.promptOnCancel && this._dirty) {
            if (confirm("You have unsaved changes. Are you " +
                        "sure you want to discard them?")) {
                this.cancel(true);
            }

            return;
        }

        this.hideEditor();
        this.element.triggerHandler("cancel", [this._initialValue]);
    },

    field: function() {
        return this._field;
    },

    value: function() {
        return this._field.val();
    },

    showEditor: function(preventAnimation) {
        var self = this,
            elHeight,
            newHeight;

        if (this._editIcon) {
            if (this.options.multiline && !preventAnimation) {
                this._editIcon
                    .animate({
                        opacity: 0
                    },
                    this.options.fadeSpeedMS,
                    'swing',
                    function() {
                        self._editIcon.css({
                            opacity: 100,
                            visibility: 'hidden'
                        });
                    });
            } else {
                this._editIcon.css('visibility', 'hidden');
            }
        }

        this.element.hide();
        this._form.show();

        if (this.options.multiline) {
            elHeight = this.element.outerHeight();
            newHeight = elHeight + this.options.extraHeight;

            this._fitWidthToParent();

            if (this.options.matchHeight) {
                // TODO: Set autosize min height
                this._field
                    .autoSizeTextArea("setMinHeight", newHeight)
                    .css("overflow", "hidden");

                if (preventAnimation) {
                    this._field.height(newHeight);
                } else {
                    this._field
                        .height(elHeight)
                        .animate({
                            height: newHeight
                        }, this.options.fadeSpeedMS);
                }
            } else {
                /*
                 * If there's significant processing that happens between the
                 * text and what's displayed in the element, it's likely that
                 * the rendered size will be different from the editor size. In
                 * that case, don't try to match sizes, just ask the field to
                 * auto-size itself to the size of the source text.
                 */
                self._field.autoSizeTextArea('autoSize', true, false, elHeight);
            }

            if (this._buttons) {
                if (preventAnimation) {
                    this._buttons.show();
                } else {
                    this._buttons.fadeIn();
                }
            }
        } else if (this._buttons) {
            this._buttons.show();
        }

        /* Execute this after the animation, if we performed one. */
        this._field.queue(function() {
            if (self.options.multiline) {
                self._field.css("overflow", "auto");
            }

            self._fitWidthToParent();

            if (self.options.focusOnOpen) {
                self._field.focus();
            }

            if (!self.options.multiline) {
                self._field[0].select();
            }

            self._field.dequeue();
        });
    },

    hideEditor: function() {
        var self = this;

        if (self.options.forceOpen) {
            return;
        }

        this._field.blur();

        if (this._buttons) {
            this._buttons.fadeOut(this.options.fadeSpeedMS);
        }

        if (this._editIcon) {
            if (this.options.multiline) {
                this._editIcon
                    .css({
                        opacity: 0,
                        visibility: 'visible'
                    })
                    .animate({
                        opacity: 100
                    }, this.options.fadeSpeedMS);
            } else {
                this._editIcon.css('visibility', 'visible');
            }
        }

        if (this.options.multiline && this._editing) {
            this._field
                .css("overflow", "hidden")
                .animate({
                    height: this.element.outerHeight()
                }, this.options.fadeSpeedMS);
        }

        this._field.queue(function() {
            self.element.show();
            self._form.hide();
            self._field.dequeue();
        });

        this._editing = false;
        // Only update _dirty state after setting _editing to false.
        this._updateDirtyState();
    },

    dirty: function() {
        return this._dirty;
    },

    _updateDirtyState: function() {
        var value = (this.options.hasRawValue
                     ? this.value()
                     : this.value().htmlEncode()),
            curDirtyState = this._editing &&
                            this._normalizeText(this._initialValue) !=
                            value;

        if (this._dirty != curDirtyState) {
            this._dirty = curDirtyState;
            this.element.triggerHandler("dirtyStateChanged", [this._dirty]);
        }
    },

    _fitWidthToParent: function() {
        if (!this._editing) {
            return;
        }

        if (this.options.multiline) {
            this._field
                .css({
                    '-webkit-box-sizing': 'border-box',
                    '-moz-box-sizing': 'border-box',
                    'box-sizing': 'border-box',
                    'width': '100%'
                });
        } else {
            var formParent = this._form.parent();

            /*
             * First make the field really small so it will fit on the
             * first line, then figure out the offset and use it calculate
             * the desired width.
             */
            this._field
                .css("min-width", this.element.innerWidth())
                .width(0)
                .outerWidth(formParent.innerWidth() -
                            (this._form.offset().left -
                             formParent.offset().left) -
                            this._field.getExtents("bmp", "lr") -
                            this._editIcon.width() -
                            (this._buttons ? this._buttons.outerWidth() : 0));
        }
    },

    _normalizeText: function(str) {
        if (this.options.stripTags) {
            /*
             * Turn <br>s back into newlines before stripping out all
             * other tags. Without this, we lose multi-line data when
             * editing an old comment.
             */
            str = str.replace(/<br>/g, '\n');
            str = str.stripTags().strip();
        }

        if (!this.options.multiline) {
            str = str.replace(/\s{2,}/g, " ");
        }

        return str;
    }
});

$.ui.inlineEditor.getter = "dirty field value";

/* Allows quickly looking for dirty inline editors. Those dirty things. */
$.expr[':'].inlineEditorDirty = function(a) {
    return $(a).inlineEditor("dirty");
};


})(jQuery);

// vim: set et:
