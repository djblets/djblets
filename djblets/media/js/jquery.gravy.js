/*
 * Copyright 2008-2010 Christian Hammond.
 * Copyright 2010-2012 Beanbag, Inc.
 *
 * Licensed under the MIT license.
 */
(function($) {

var userAgent = navigator.userAgent.toLowerCase();

$.extend($.browser, {
    chrome: /chrome/.test(userAgent),
    mobileSafari: /webkit.*mobile/.test(userAgent),
    mobileSafariIPad: /ipad.*webkit.*mobile/.test(userAgent)
});

$.fn.old_html = $.fn.html;


/*
 * IE has broken innerHTML support. Newlines and other whitespace is stripped
 * from the HTML, even when inserting into a <pre>. This doesn't happen,
 * however, if the whole html is wrapped in a <pre> before being set.
 * So our new version of html() wraps it and then removes that inner <pre>
 * tag.
 */
$.fn.html = function(value) {
    var removePre = false;

    if ($.browser.msie && value !== undefined && this[0] &&
        /^(pre|textarea)$/i.test(this[0].tagName)) {
        value = "<pre>" + value + "</pre>";
        removePre = true;
    }

    var ret = this.old_html.apply(this, value === undefined ? [] : [value]);

    if (removePre) {
        var preTag = this.children();
        preTag.replaceWith(preTag.contents());
    }

    return ret;
}

/*
 * $.offset() on Safari on the iPad returns incorrect values, so this code
 * will compensate.
 *
 * See http://dev.jquery.com/ticket/6446
 */
if ($.browser.mobileSafariIPad) {
    $.fn.old_offset = $.fn.offset;

    $.fn.offset = function(offset) {
        var result = this.old_offset(offset);

        if (result.top) {
            result.top -= window.scrollY;
        }

        if (result.left) {
            result.left -= window.scrollX;
        }

        return result;
    }
}

jQuery.fn.extend({
    /*
     * Sets one or more elements' visibility based on the specified value.
     *
     * @param {bool} visible The visibility state.
     *
     * @return {jQuery} This jQuery.
     */
    setVisible: function(visible) {
        return $(this).each(function() {
            if (visible) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    },

    /*
     * Sets the position of an element.
     *
     * @param {int}    left     The new left position.
     * @param {int}    top      The new top position.
     * @param {string} posType  The optional position type.
     *
     * @return {jQuery} This jQuery.
     */
    move: function(left, top, posType) {
        return $(this).each(function() {
            $(this).css({
                left: left,
                top: top
            });

            if (posType) {
                $(this).css("position",
                    (posType == "fixed" && $.browser.msie &&
                     $.browser.version == 6)
                    ? "absolute" : posType);
            }
        });
    },

    /*
     * Scrolls an element so that it's fully in view, if it wasn't already.
     *
     * @return {jQuery} This jQuery.
     */
    scrollIntoView: function() {
        return $(this).each(function() {
            var offset = $(this).offset();
            var scrollLeft = $(document).scrollLeft();
            var elLeft = (scrollLeft + $(window).width()) -
                         (offset.left + $(this).outerWidth(true));

            if (elLeft < 0) {
                $(window).scrollLeft(scrollLeft - elLeft);
            }

            var scrollTop = $(document).scrollTop();
            var elTop = (scrollTop + $(window).height()) -
                        (offset.top + $(this).outerHeight(true));

            if (elTop < 0) {
                $(window).scrollTop(scrollTop - elTop);
            }
        });
    }
});

$.fn.getExtents = function(types, sides) {
    var val = 0;

    this.each(function() {
        var self = $(this);

        for (var t = 0; t < types.length; t++) {
            var type = types.charAt(t);

            for (var s = 0; s < sides.length; s++) {
                var side = sides.charAt(s);
                var prop;

                if (type == "b") {
                    type = "border";
                } else if (type == "m") {
                    type = "margin";
                } else if (type == "p") {
                    type = "padding";
                }

                if (side == "l" || side == "left") {
                    side = "Left";
                } else if (side == "r" || side == "right") {
                    side = "Right";
                } else if (side == "t" || side == "top") {
                    side = "Top";
                } else if (side == "b" || side == "bottom") {
                    side = "Bottom";
                }

                prop = type + side;

                if (type == "border") {
                    prop += "Width";
                }

                var i = parseInt(self.css(prop));

                if (!isNaN(i)) {
                    val += i;
                }
            }
        }
    });

    return val;
};


/*
 * If appropriate, reload gravatar <img> tags with retina resolution
 * equivalents.
 */
$.fn.retinaGravatar = function() {
    if (window.devicePixelRatio > 1) {
        $(this).each(function() {
            var src = $(this).attr('src'),
                parts = src.split('=', 2),
                baseurl,
                size;

            if (parts.length == 2) {
                baseurl = parts[0];
                size = parseInt(parts[1], 10);

                $(this)
                    .attr('src', baseurl + '=' + Math.floor(size * window.devicePixelRatio))
                    .removeClass('gravatar')
                    .addClass('gravatar-retina');
            } else {
                console.log('Failed to parse URL for gravatar ' + src);
            }
        });
    }
};


/*
 * Auto-sizes a text area to make room for the contained content.
 */
$.widget("ui.autoSizeTextArea", {
    options: {
        fadeSpeedMS: 200,
        growOnKeyUp: true,
        minHeight: 100
    },

    _init: function() {
        var self = this;

        if ($.browser.safari && $.browser.version < 531.9) {
            /*
             * Older versions of WebKit have some crasher bugs and height
             * computation bugs that prevent this from working. In those
             * cases, we just want to turn off auto-sizing altogether.
             */
            return;
        }

        this._proxyEl = $("<pre/>")
            .appendTo("body")
            .move(-10000, -10000, "absolute");

        if (!$.browser.msie) {
            /*
             * Set white-space to pre-wrap on browsers that support it.
             * Most browsers will either ignore this or accept it as the
             * main value if they understand it. IE, however, will complain,
             * so we don't want to set it there. (Bug #1349)
             */
            this._proxyEl.css("white-space", "pre-wrap"); // Standards-compliant
        }

        if ($.browser.mozilla) {
            this._proxyEl.css("white-space", "-moz-pre-wrap"); // Mozilla, 1999+
        } else if ($.browser.opera) {
            // Opera 4-6
            this._proxyEl.css("white-space", "-pre-wrap");

            // Opera 7
            this._proxyEl.css({
                "white-space": "-o-pre-wrap",
                "word-wrap": "break-word"
            });
        }

        this.element.css("overflow", "hidden");
        this.oldLength = this.element.val().length;

        if (this.options.growOnKeyUp) {
            this.element
                .keyup(function() {
                    self.autoSize();
                });
        }
    },

    destroy: function() {
        this._proxyEl.remove();
        $.Widget.prototype.destroy.call(this);
    },

    /*
     * Auto-sizes a text area to match the content.
     *
     * This works by setting a proxy element to match the exact width of
     * our text area and then filling it with text. The proxy element will
     * grow to accommodate the content. We then set the text area to the
     * resulting width.
     */
    autoSize: function(force, animate, animateFrom) {
        var needsResize = false,
            newLength = this.element.val().length,
            newHeight = 0,
            normHeight = this.element[0].scrollHeight +
                         (this.element.height() -
                          this.element[0].clientHeight),
            targetHeight;

        if (normHeight != this.element.height()) {
            /* We know the height grew, so queue a resize. */
            needsResize = true;
            newHeight = normHeight;
        } else if (this.oldLength > newLength || force) {
            /* The size may have decreased. Check the number of lines. */
            needsResize = true;

            this._proxyEl
                .width(this.element.width())
                .move(-10000, -10000)
                .text(this.element.val() + "\n");
            newHeight = this._proxyEl.outerHeight();
        }

        if (needsResize) {
            targetHeight = Math.max(this.options.minHeight, newHeight);

            if (animate) {
                this.element
                    .height(animateFrom)
                    .animate({
                        height: targetHeight
                    }, this.options.fadeSpeedMS)
                    .triggerHandler("resize");
            } else {
                this.element
                    .height(targetHeight)
                    .triggerHandler("resize");
            }
        }

        this.oldLength = newLength;
    },

    setMinHeight: function(minHeight) {
        this.options.minHeight = minHeight;
    }
});


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
            this._editIcon.css('visibility', 'hidden');
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

        if (this.options.multiline && $.browser.msie) {
            this._field.text(value);
        } else {
            this._field.val(value);
        }

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
                    })
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
                this._field.autoSizeTextArea('autoSize', true,
                                             !preventAnimation, elHeight);
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
        var curDirtyState = this._editing &&
                             this._normalizeText(this._initialValue) !=
                             this.value().htmlEncode();

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
            str = str.replace(/\<br\>/g, '\n');
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


jQuery.fn.positionToSide = function(el, options) {
    options = jQuery.extend({
        side: 'b',
        distance: 0,
        fitOnScreen: false
    }, options);

    var offset = $(el).offset();
    var thisWidth = this.width();
    var thisHeight = this.height();
    var elWidth = el.width();
    var elHeight = el.height();

    var scrollLeft = $(document).scrollLeft();
    var scrollTop = $(document).scrollTop();
    var scrollWidth = $(window).width();
    var scrollHeight = $(window).height();

    return $(this).each(function() {
        var bestLeft = null;
        var bestTop = null;

        for (var i = 0; i < options.side.length; i++) {
            var side = options.side.charAt(i);
            var left = 0;
            var top = 0;

            if (side == "t") {
                left = offset.left;
                top = offset.top - thisHeight - options.distance;
            } else if (side == "b") {
                left = offset.left;
                top = offset.top + elHeight + options.distance;
            } else if (side == "l") {
                left = offset.left - thisWidth - options.distance;
                top = offset.top;
            } else if (side == "r") {
                left = offset.left + elWidth + options.distance;
                top = offset.top;
            } else {
                continue;
            }

            if (left >= scrollLeft &&
                left + thisWidth - scrollLeft < scrollWidth &&
                top >= scrollTop &&
                top + thisHeight - scrollTop < scrollHeight) {
                bestLeft = left;
                bestTop = top;
                break;
            } else if (bestLeft == null) {
                bestLeft = left;
                bestTop = top;
            }
        }

        if (options.fitOnScreen) {
            bestLeft = Math.min(bestLeft,
                                scrollLeft + scrollWidth -
                                thisWidth);
            bestTop = Math.min(bestTop,
                               scrollTop + scrollHeight -
                               thisHeight);
        }

        $(this).move(bestLeft, bestTop, "absolute");
    });
};


jQuery.fn.delay = function(msec) {
    return $(this).each(function() {
        var self = $(this);
        self.queue(function() {
            window.setTimeout(function() { self.dequeue(); }, msec);
        });
    });
}


$.widget("ui.modalBox", {
    options: {
        buttons: [$('<input type="button" value="Close"/>')],
        container: 'body',
        discardOnClose: true,
        fadeBackground: true,
        modalBoxButtonsClass: "modalbox-buttons",
        modalBoxContentsClass: "modalbox-contents",
        modalBoxTitleClass: "modalbox-title",
        stretchX: false,
        stretchY: false,
        title: null
    },

    _init: function() {
        var self = this;

        if (this.options.fadeBackground) {
            this.bgbox = $("<div/>")
                .addClass("modalbox-bg")
                .appendTo(this.options.container)
                .css({
                    "background-color": "#000",
                    opacity: 0,
                    zIndex: 99
                })
                .move(0, 0, "fixed")
                .width("100%")
                .height("100%")
                .keydown(function(e) { e.stopPropagation(); });
        }

        this.box = $("<div/>")
            .addClass("modalbox")
            .move(0, 0, "absolute")
            .css('z-index', 2000)
            .keydown(function(e) { e.stopPropagation(); });

        if (this.options.boxID) {
            this.box.attr('id', this.options.boxID);
        }

        this.inner = $("<div/>")
            .appendTo(this.box)
            .addClass("modalbox-inner")
            .css({
                position: "relative",
                width: "100%",
                height: "100%"
            });

        if (this.options.title) {
            this.titleBox = $("<h1/>")
                .appendTo(this.inner)
                .addClass(this.options.modalBoxTitleClass)
                .text(this.options.title);
        }

        this.element
            .appendTo(this.inner)
            .addClass(this.options.modalBoxContentsClass)
            .bind("DOMSubtreeModified", function() {
                self.resize();
            });

        this._buttons = $("<div/>")
            .appendTo(this.inner)
            .addClass(this.options.modalBoxButtonsClass)
            .click(function(e) {
                /* Check here so that buttons can call stopPropagation(). */
                if (e.target.tagName == "INPUT") {
                    self.element.modalBox("destroy");
                }
            });

        this.box.appendTo(this.options.container);

        $.each(this.options.buttons, function() {
            $(this).appendTo(self._buttons);
        });

        if (this.options.fadeBackground) {
            this.bgbox.fadeTo(800, 0.7);
        }

        $(window).bind("resize.modalbox", function() {
            self.resize();
        });

        this.resize();
    },

    destroy: function() {
        var self = this;

        if (!this.element.data("modalBox"))
            return;

        this.element
            .removeData("modalBox")
            .unbind("resize.modalbox")
            .css("position", "static");

        if (this.options.fadeBackground) {
            this.bgbox.fadeOut(350, function() {
                self.bgbox.remove();
            });
        }

        if (!this.options.discardOnClose) {
            this.element.appendTo(this.options.container);
        }

        this.box.remove();
    },

    buttons: function() {
        return this._buttons;
    },

    resize: function() {
        var marginHoriz = $("body").getExtents("m", "lr");
        var marginVert  = $("body").getExtents("m", "tb");
        var winWidth    = $(window).width()  - marginHoriz;

        /* Fix a jQuery/Opera 9.5 bug with broken window heights */
        var winHeight = ($.browser.opera && $.browser.version > "9.5" &&
                         $.fn.jquery <= "1.2.6"
                         ? document.documentElement["clientHeight"]
                         : $(window).height())
                        - marginVert;

        if ($.browser.msie && $.browser.version == 6) {
            /* Width/height of 100% don't really work right in IE6. */
            this.bgbox.width($(window).width());
            this.bgbox.height($(window).height());
        }

        if (this.options.stretchX) {
            this.box.width(winWidth -
                           this.box.getExtents("bmp", "lr") -
                           marginHoriz);
        }

        if (this.options.stretchY) {
            this.box.height(winHeight -
                            this.box.getExtents("bmp", "tb") -
                            marginVert);

            this.element.height(this._buttons.position().top -
                                this.element.position().top -
                                this.element.getExtents("m", "tb"));
        } else {
            this.box.height(this.element.position().top +
                            this.element.outerHeight(true) +
                            this._buttons.outerHeight(true));
        }

        this.box.move((winWidth  - this.box.outerWidth(true))  / 2,
                      (winHeight - this.box.outerHeight(true)) / 2,
                      "fixed");

        this.element.triggerHandler("resize");
    }
});

$.ui.modalBox.getter = "buttons";


jQuery.tooltip = function(el, options) {
    options = jQuery.extend({
        side: 'b'
    }, options);

    var self = $("<div/>")
        .addClass("tooltip")
        .hide()
        .appendTo("body");

    if ($.browser.mobileSafari) {
        /* Tooltips don't make sense on touchpads. Silently ignore. */
        return self;
    }

    el.hover(
        function() {
            if (self.children()) {
                self
                    .positionToSide(el, {
                        side: options.side,
                        distance: 10
                    })
                    .show();
            }
        },
        function() {
            self.hide();
        });

    return self;
};

$.fn.proxyTouchEvents = function(events) {
    events = events || "touchstart touchmove touchend";

    return $(this).bind(events, function(event) {
        var touches = event.originalEvent.changedTouches;
        var first = touches[0];
        var type = "";

        switch (event.type) {
        case "touchstart":
            type = "mousedown";
            break;

        case "touchmove":
            type = "mousemove";
            break;

        case "touchend":
            type = "mouseup";
            break;
        }

        var mouseEvent = document.createEvent("MouseEvent");
        mouseEvent.initMouseEvent(type, true, true, window, 1,
                                  first.screenX, first.screenY,
                                  first.clientX, first.clientY,
                                  false, false, false, false, 0, null);

        if (!event.target.dispatchEvent(mouseEvent)) {
            event.preventDefault();
        }
    });
};

jQuery.extend(String.prototype, {
    strip: function() {
        return this.replace(/^\s+/, '').replace(/\s+$/, '');
    },

    stripTags: function() {
        return this.replace(/<\/?[^>]+>/gi, '');
    },

    htmlEncode: function() {
        if (this == "") {
          return "";
        }

        str = this.replace(/&/g, "&amp;");
        str = str.replace(/</g, "&lt;");
        str = str.replace(/>/g, "&gt;");

        return str;
    },

    htmlDecode: function() {
        if (this == "") {
          return "";
        }

        str = this.replace(/&amp;/g, "&");
        str = str.replace(/&lt;/g, "<");
        str = str.replace(/&gt;/g, ">");

        return str;
    },

    truncate: function(numChars) {
        numChars = numChars || 100;

        var str = this.toString();

        if (this.length > numChars) {
            str = this.substring(0, numChars - 3); // minus length of "..."
            i = str.lastIndexOf(".");

            if (i != -1) {
                str = str.substring(0, i + 1);
            }

            str += "...";
        }

        return str;
    }
});


var queues = {};
var queuesInProgress = {};

/*
 * A set of utility functions for implementing a queue of functions.
 * Functions are added to the queue and, when their operation is complete,
 * they are to call next(), which will trigger the next function in the
 * queue.
 *
 * There can be multiple simultaneous queues going at once. They're identified
 * by queue names that are passed to funcQueue().
 */
$.funcQueue = function(name) {
    var self = this;

    if (!queues[name]) {
        queues[name] = [];
    }

    /*
     * Adds a function to the queue.
     *
     * This will just add the item to the queue. To start the queue, run
     * start() after adding the function.
     *
     * @param {function} func    The function to add.
     * @param {object}   context The context in which to invoke the function.
     */
    this.add = function(func, context) {
        if (func) {
            queues[name].push([func, context]);
        }
    };

    /*
     * Invokes the next function in the queue.
     *
     * This should only be called when a task in the queue is finished.
     * Calling this function will immediately process the next item in the
     * queue, out of order.
     *
     * Callers wanting to ensure the queue is running after adding the
     * initial item should call start() instead.
     */
    this.next = function() {
        var info,
            func,
            context;

        if (queuesInProgress[name]) {
            info = queues[name].shift();

            if (info) {
                func = info[0];
                context = info[1];

                func.call(context);
            } else {
                queuesInProgress[name] = false;
            }
        }
    };

    /*
     * Begins the queue.
     *
     * If a queue has already been started, this will do nothing.
     */
    this.start = function() {
        if (!queuesInProgress[name] && queues[name].length > 0) {
            queuesInProgress[name] = true;
            self.next();
        }
    };

    /*
     * Clears the queue, removing all pending functions.
     */
    this.clear = function() {
        queues[name] = [];
        queuesInProgress[name] = false;
    };

    return this;
}

})(jQuery);

// vim: set et:
