/**
 * Settings for the avatar configuration form.
 *
 * Model attributes:
 *     configuration (object):
 *         A mapping of each service ID (`string``) to its configuration object
 *         (``object``).
 *
 *     serviceID (string):
 *         The currently selected service ID.
 *
 *     services (object):
 *         A mapping of each service ID (``string``) to its properties
 *         (``object``), such as  whether or not is is configurable.
 */
Djblets.Avatars.Settings = Backbone.Model.extend({
    defaults() {
        return {
            configuration: {},
            serviceID: null,
            services: {}
        };
    }
});
