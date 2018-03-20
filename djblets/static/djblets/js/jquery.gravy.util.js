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


if (!window.Djblets) {
    window.Djblets = {};
}


if ($.support.touch === undefined) {
    $.support.touch = ('ontouchstart' in window ||
                       navigator.msMaxTouchPoints);
}

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
                $(this).css("position", posType);
            }
        });
    },

    /*
     * Scrolls an element so that it's fully in view, if it wasn't already.
     *
     * @return {jQuery} This jQuery.
     */
    scrollIntoView: function() {
        var $document = $(document),
            $window = $(window);

        return $(this).each(function() {
            var $this = $(this),
                offset = $this.offset(),
                scrollLeft = $document.scrollLeft(),
                scrollTop = $document.scrollTop(),
                elLeft = (scrollLeft + $window.width()) -
                         (offset.left + $this.outerWidth(true)),
                elTop = (scrollTop + $window.height()) -
                         (offset.top + $this.outerHeight(true));

            if (elLeft < 0) {
                $window.scrollLeft(scrollLeft - elLeft);
            }

            if (elTop < 0) {
                $window.scrollTop(scrollTop - elTop);
            }
        });
    }
});

$.fn.getExtents = function(types, sides) {
    var val = 0;

    this.each(function() {
        var self = $(this),
            value,
            type,
            side,
            prop,
            t,
            s,
            i;

        for (t = 0; t < types.length; t++) {
            type = types.charAt(t);

            for (s = 0; s < sides.length; s++) {
                side = sides.charAt(s);

                if (type === "b") {
                    type = "border";
                } else if (type === "m") {
                    type = "margin";
                } else if (type === "p") {
                    type = "padding";
                }

                if (side === "l" || side === "left") {
                    side = "Left";
                } else if (side === "r" || side === "right") {
                    side = "Right";
                } else if (side === "t" || side === "top") {
                    side = "Top";
                } else if (side === "b" || side === "bottom") {
                    side = "Bottom";
                }

                prop = type + side;

                if (type === "border") {
                    prop += "Width";
                }

                value = self.css(prop);

                if (value.indexOf('.') === -1) {
                    i = parseInt(value, 10);
                } else {
                    i = parseFloat(value, 10);
                }

                if (!isNaN(i)) {
                    val += i;
                }
            }
        }
    });

    return val;
};


/**
 * Positions an element to the side of another element.
 *
 * This can take a number of options to customize how the element is
 * positioned.
 *
 * Args:
 *     $el (jQuery):
 *         The jQuery-wrapped element to position beside.
 *
 *     options (object):
 *         Options to control the positioning.
 *
 * Option Args:
 *     side (string):
 *         A string of side codes in the order of priority. Each will be
 *         checked to determine if the element can be positioned to that
 *         side. If multiple sides are provided, then this will loop through
 *         them in order, trying to find the best top and the best left that
 *         fit on the screen.
 *
 *         The following codes are generally used to position this element
 *         outside of ``el``:
 *
 *         ``t``:
 *             Position the bottom of this element relative to the top of
 *             ``el``.
 *
 *         ``b``:
 *             Position the top of this element relative to the bottom of
 *             ``el``.
 *
 *         ``l``:
 *             Position the right of this element relative to the left of
 *             ``el``.
 *
 *         ``r``:
 *             Position the left of this element relative to the right of
 *             ``el``.
 *
 *         The following codes are generally used to position this element
 *         inside of ``el``:
 *
 *         ``T``:
 *             Position the top of this element relative to the top of ``el``.
 *
 *         ``B``:
 *             Position the bottom of this element relative to the bottom of
 *             ``el``.
 *
 *         ``L``:
 *             Position the left of this element relative to the left of
 *             ``el``.
 *
 *         ``R``:
 *             Position the right of this element relative to the right of
 *             ``el``.
 *
 *         This defaults to ``b``.
 *
 *     distance (number):
 *         The distance to add relative to ``$el``'s calculated anchoring
 *         point, based on the side chosen. This will be used as the default
 *         value for all other distance options, unless more specific distances
 *         are provided.
 *
 *         This defaults to 0.
 *
 *     xDistance (number):
 *         The distance to use for X-based sides (``l``, ``L``, ``r``, ``R``),
 *         unless overridden by a more specific distance option. Defaults to
 *         the value of ``distance``.
 *
 *     yDistance (number):
 *         The distance to use for Y-based sides (``t``, ``T``, ``b``, ``B``),
 *         unless overridden by a more specific distance options. Defaults to
 *         the value of ``distance``.
 *
 *     tDistance (number):
 *         The distance to use for the ``t`` side. Defaults to the value of
 *         ``yDistance``.
 *
 *     TDistance (number):
 *         The distance to use for the ``T`` side. Defaults to the value of
 *         ``yDistance``.
 *
 *     bDistance (number):
 *         The distance to use for the ``b`` side. Defaults to the value of
 *         ``yDistance``.
 *
 *     BDistance (number):
 *         The distance to use for the ``B`` side. Defaults to the value of
 *         ``yDistance``.
 *
 *     lDistance (number):
 *         The distance to use for the ``l`` side. Defaults to the value of
 *         ``xDistance``.
 *
 *     lDistance (number):
 *         The distance to use for the ``L`` side. Defaults to the value of
 *         ``xDistance``.
 *
 *     rDistance (number):
 *         The distance to use for the ``r`` side. Defaults to the value of
 *         ``xDistance``.
 *
 *     RDistance (number):
 *         The distance to use for the ``R`` side. Defaults to the value of
 *         ``xDistance``.
 *
 *     xOffset (number):
 *         A X offset to apply to the element when matching only a
 *         vertical side (``t``, ``T``, ``b``, or ``B``). This will add to
 *         or subtract from the left offset of ``$el``.
 *
 *         This defaults to 0.
 *
 *     yOffset (number):
 *         A Y offset to apply to the element when matching only a
 *         vertical side (``l``, ``L``, ``r``, or ``R``). This will add to
 *         or subtract from the top offset of ``$el``.
 *
 *         This defaults to 0.
 *
 *     fitOnScreen (boolean):
 *         If set, the element's position will be adjusted so that it is
 *         fully viewable on screen. By default, this is not set.
 *
 * Returns:
 *     jQuery:
 *     The matching elements used for this function.
 */
$.fn.positionToSide = function($el, options) {
    var offset = $el.offset(),
        elWidth = $el.width(),
        elHeight = $el.height(),
        $document = $(document),
        $window = $(window),
        scrollLeft = $document.scrollLeft(),
        scrollTop = $document.scrollTop(),
        scrollWidth = $window.width(),
        scrollHeight = $window.height();

    options = $.extend({
        side: 'b',
        xDistance: options.distance || 0,
        yDistance: options.distance || 0,
        xOffset: 0,
        yOffset: 0,
        fitOnScreen: false
    }, options);

    return $(this).each(function() {
        var $this = $(this),
            thisWidth = $this.outerWidth(),
            thisHeight = $this.outerHeight(),
            bestLeft = null,
            bestTop = null,
            side,
            left,
            top,
            i;

        for (i = 0; i < options.side.length; i++) {
            side = options.side.charAt(i);
            left = null;
            top = null;

            if (side === 't') {
                top = offset.top - thisHeight -
                      (options.tDistance !== undefined
                       ? options.tDistance
                       : options.yDistance);
            } else if (side === 'T') {
                top = offset.top +
                      (options.TDistance !== undefined
                       ? options.TDistance
                       : options.yDistance);
            } else if (side === 'b') {
                top = offset.top + elHeight +
                      (options.bDistance !== undefined
                       ? options.bDistance
                       : options.yDistance);
            } else if (side === 'B') {
                top = offset.top + elHeight - thisHeight -
                      (options.BDistance !== undefined
                       ? options.BDistance
                       : options.yDistance);
            } else if (side === 'l') {
                left = offset.left - thisWidth -
                       (options.lDistance !== undefined
                        ? options.lDistance
                        : options.xDistance);
            } else if (side === 'L') {
                left = offset.left +
                       (options.LDistance !== undefined
                        ? options.LDistance
                        : options.xDistance);
            } else if (side === 'r') {
                left = offset.left + elWidth +
                       (options.rDistance !== undefined
                        ? options.rDistance
                        : options.xDistance);
            } else if (side === 'R') {
                left = offset.left + elWidth - thisWidth -
                       (options.RDistance !== undefined
                        ? options.RDistance
                        : options.xDistance);
            } else {
                continue;
            }

            if ((left !== null &&
                 left >= scrollLeft &&
                 left + thisWidth - scrollLeft < scrollWidth) ||
                (top !== null &&
                 top >= scrollTop &&
                 top + thisHeight - scrollTop < scrollHeight)) {
                bestLeft = left;
                bestTop = top;
                break;
            } else if (bestLeft === null && bestTop === null) {
                bestLeft = left;
                bestTop = top;
            }
        }

        if (bestLeft === null) {
            bestLeft = offset.left + options.xOffset;
        }

        if (bestTop === null) {
            bestTop = offset.top + options.yOffset;
        }

        if (options.fitOnScreen) {
            bestLeft = Math.max(
                Math.min(bestLeft, scrollLeft + scrollWidth - thisWidth),
                scrollLeft);
            bestTop = Math.max(
                Math.min(bestTop, scrollTop + scrollHeight - thisHeight),
                scrollTop);
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
    var stateKey = 'gravy-proxy-touch-state';

    function simulateMouseEvent(event, type, touch, relatedTarget) {
        var mouseEvent = document.createEvent('MouseEvent');

        mouseEvent.initMouseEvent(type, true, true, window, 1,
                                  touch.screenX, touch.screenY,
                                  touch.clientX, touch.clientY,
                                  false, false, false, false, 0,
                                  relatedTarget || null);

        if (!event.target.dispatchEvent(mouseEvent)) {
            event.preventDefault();
        }
    }

    events = events || 'touchstart touchmove touchend';

    return $(this).on(events, function(event) {
        var $this = $(this),
            touches = event.originalEvent.changedTouches,
            firstTouch,
            hoverEl,
            touchState;

        if (touches.length !== 1) {
             // Ignore this event. We don't want to get in the way of gestures.
             return;
        }

        firstTouch = event.originalEvent.changedTouches[0];

        switch (event.type) {
        case 'touchstart':
            $this.data(stateKey, {
                lastEl: document.elementFromPoint(firstTouch.clientX,
                                                  firstTouch.clientY)
            });
            simulateMouseEvent(event, 'mousedown', firstTouch);
            break;

        case 'touchmove':
            touchState = $this.data(stateKey);
            hoverEl = document.elementFromPoint(firstTouch.clientX,
                                                firstTouch.clientY);

            if (touchState.lastEl !== hoverEl) {
                simulateMouseEvent(event, 'mouseout', firstTouch,
                                   touchState.lastEl);

                touchState.lastEl = hoverEl;
                simulateMouseEvent(event, 'mouseover', firstTouch,
                                   hoverEl);
            }

            simulateMouseEvent(event, 'mousemove', firstTouch);
            break;

        case 'touchend':
        case 'touchcancel':
            simulateMouseEvent(event, 'mouseup', firstTouch);
            $this.data(stateKey, null);
            break;
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

            if (i !== -1) {
                str = str.substring(0, i + 1);
            }

            str += "...";
        }

        return str;
    }
});


/**
 * Return an object/prototype/attribute given a dotted path.
 *
 * This will take a path as a string in the form of ``Djblets.Foo.Bar`` and
 * return the matching object, if found. By default, this starts at
 * ``window``, but any starting object can be provided.
 *
 * If not found, this will assert with a failure.
 *
 * Args:
 *     path (string):
 *         The dotted path to look up.
 *
 *     obj (object, optional):
 *         The object to use as the starting point for lookups. If not
 *         provided, ``window`` is used.
 *
 * Returns:
 *     object:
 *     The object matching the dotted path.
 */
Djblets.getObjectByName = function(name, obj) {
    var cls = name.split('.').reduce(function(o, i) { return o[i]; },
                                     obj || window);
    console.assert(cls, 'Invalid class path "' + name + '".');

    return cls;
};


})(jQuery);

// vim: set et:
