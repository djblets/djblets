/**
 * Parse a query string for key/value pairs.
 *
 * This takes a query string in the provided URL and parses it for standard
 * key/value pairs, returning an object representing those keys and values.
 * It can handle keys without values and optionally store multiple values
 * listed for the same key.
 *
 * Args:
 *     url (string):
 *         The URL containing a query string to parse.
 *
 *     options (object, optional):
 *         Options for controlling the parsing.
 *
 * Option Args:
 *     allowMultiValue (boolean):
 *         Whether to store multiple values for the same key, if found in
 *         the query string. The value for such a key will be an array of all
 *         values. If ``false`` (the default), only last value for a key will
 *         be stored.
 *
 * Returns:
 *     object:
 *     The resulting keys and values representing the query string.
 *
 *     If there was a query string item that did not have a value (in other
 *     words, no ``=`` was present), then its value will be ``null``.
 *
 *     If ``options.allowMultiValue`` is ``true``, and a key was used more
 *     than once, then its value will be a list of all values in the query
 *     string for that key.
 */
Djblets.parseQueryString = function(url, options={}) {
    const allowMultiValue = options.allowMultiValue;

    let j = url.indexOf('?');
    let queryString;

    if (j === -1) {
        /* Assume the whole thing is a query string. */
        queryString = url;
    } else {
        queryString = url.substr(j + 1);
    }

    const query = {};

    if (queryString.length === 0) {
        return query;
    }

    const queryParams = queryString.split('&');

    for (let i = 0; i < queryParams.length; i++) {
        const queryParam = queryParams[i];
        let key;
        let value;

        j = queryParam.indexOf('=');

        if (j === -1) {
            key = decodeURIComponent(queryParam);
            value = null;
        } else {
            key = decodeURIComponent(queryParam.substr(0, j));
            value = decodeURIComponent(queryParam.substr(j + 1));
        }

        if (allowMultiValue && query.hasOwnProperty(key)) {
            if (_.isArray(query[key])) {
                query[key].push(value);
            } else {
                query[key] = [query[key], value];
            }
        } else {
            query[key] = value;
        }
    }

    return query;
};
