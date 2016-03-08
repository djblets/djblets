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

/* Whether or not the browser supports the ``srcset`` attribute.
 *
 * All versions of IE and Edge do not support this attribute so we need to
 * polyfill for them.
 */
var supportsSourceSet = ($('<img src="" />').get().srcset === '');

/*
 * Parse the ``srcset`` attribute.
 *
 * Args:
 *     srcset (String):
 *         The source set, as a string of comma-separated URLs and descriptors.
 *
 * Returns:
 *     Object: A mapping of descriptors to URLs.
 */
function parseSourceSet(srcset) {
    var urls = {},
        sources = srcset.split(','),
        i,
        parts,
        url,
        descriptor;

    for (i = 0; i < sources.length; i++) {
        parts = sources[i].trim().split(' ');
        url = parts[0];

        if (parts.length !== 2) {
            descriptor = parts[1];
        } else {
            descriptor = '1x';
        }

        urls[descriptor] = url;
    }

    return urls;
}

/*
 * If appropriate, reload avatar <img> tags with retina resolution equivalents.
 */
$.fn.retinaAvatar = function() {
    var pixelRatio = window.devicePixelRatio;

    if (pixelRatio > 1 && !supportsSourceSet) {
        /*
         * It is more useful to provide a 2x avatar on a 1.5 pixel ratio than
         * to provide a 1x avatar.
          */
        pixelRatio = Math.ceil(pixelRatio);

        $(this).each(function() {
            var $el = $(this),
                urls = parseSourceSet($el.attr('srcset') || ''),
                descriptor,
                url;

            for (descriptor = pixelRatio; descriptor > 0; descriptor--) {
                url = urls[descriptor + 'x'];

                if (url !== undefined) {
                    $el
                        .attr('src', url)
                        .addClass('avatar-at' + descriptor + 'x');

                    return;
                }
            }
        });
    }

    return this;
};

/*
 * If appropriate, reload gravatar <img> tags with retina resolution
 * equivalents.
 */
$.fn.retinaGravatar = function() {
    if (window.devicePixelRatio > 1) {
        $(this).each(function() {
            var $el = $(this);

            $el
                .attr('src', Djblets.getGravatarForDisplay($el.attr('src')))
                .removeClass('gravatar')
                .addClass('gravatar-retina');
        });
    }

    return this;
};


/*
 * Return a Gravatar URL most appropriate for the display.
 *
 * If on a Retina or other high-DPI display, a higher-resolution Gravatar
 * will be returned.
 *
 * Args:
 *     url (String): The URL to the Gravatar.
 *
 * Returns:
 *     String: The URL to the Gravatar best matching the current display.
 */
Djblets.getGravatarForDisplay = function(url) {
    if (window.devicePixelRatio > 1) {
        var parts = url.split('?', 2),
            params,
            param,
            baseurl,
            size,
            i;

        if (parts.length === 2) {
            baseurl = parts[0];
            params = parts[1].split('&');

            for (i = 0; i < params.length; i++) {
                param = params[i].split('=', 2);

                if (param.length === 2 && param[0] === 's') {
                    size = parseInt(param[1], 10);
                    params[i] = 's=' +
                                Math.floor(size * window.devicePixelRatio);
                }
            }

            url = baseurl + '?' + params.join('&');
        } else {
            console.log('Failed to parse URL for gravatar ' + src);
        }
    }

    return url;
};


})(jQuery);

// vim: set et:
