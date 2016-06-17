/**
 * Return a new promise with its resolver.
 *
 * Returns:
 *     array:
 *     An array of the promise and its resolver.
 */
Promise.withResolver = function withResolver() {
    let resolver;
    const promise = new Promise((resolve, reject) => {
        resolver = resolve;
    });

    return [promise, resolver];
};
