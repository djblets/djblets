(function($) {

jQuery.fn.extend({
    /*
     * Makes an element unselectable.
     */
    unselectable: function() {
        this
            .attr("unselectable", "on")
            .css({
                '-moz-user-select': 'none',
                '-khtml-user-select': 'none'
            })
            .bind('selectstart', function(evt) {
                evt.stopPropagation();
                evt.preventDefault();
            });

        return this;
    }
});


jQuery.extend(String, {
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
    }
});

var queues = {};

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
     * @param {function} func  The function to add.
     */
    this.add = function(func) {
        queues[name].push(func);
    };

    /*
     * Invokes the next function in the queue.
     */
    this.next = function() {
        if (queues[name].length == 0) {
            return;
        }

        var func = queues[name].shift();
        func();
    };

    /*
     * Begins the queue.
     */
    this.start = function() {
        self.next();
    };

    return this;
}

})(jQuery);
