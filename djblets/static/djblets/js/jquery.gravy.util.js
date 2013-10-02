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


$.fn.extend({
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
                     $.browser.version == 6) ? "absolute" : posType);
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

                var i = parseInt(self.css(prop), 10);

                if (!isNaN(i)) {
                    val += i;
                }
            }
        }
    });

    return val;
};


$.fn.positionToSide = function(el, options) {
    options = $.extend({
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
            } else if (bestLeft === null) {
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


$.fn.delay = function(msec) {
    return $(this).each(function() {
        var self = $(this);
        self.queue(function() {
            window.setTimeout(function() { self.dequeue(); }, msec);
        });
    });
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


$.extend(String.prototype, {
    strip: function() {
        return this.replace(/^\s+/, '').replace(/\s+$/, '');
    },

    stripTags: function() {
        return this.replace(/<\/?[^>]+>/gi, '');
    },

    htmlEncode: function() {
        if (this === "") {
          return "";
        }

        str = this.replace(/&/g, "&amp;");
        str = str.replace(/</g, "&lt;");
        str = str.replace(/>/g, "&gt;");

        return str;
    },

    htmlDecode: function() {
        if (this === "") {
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


})(jQuery);

// vim: set et:
