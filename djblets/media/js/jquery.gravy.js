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
