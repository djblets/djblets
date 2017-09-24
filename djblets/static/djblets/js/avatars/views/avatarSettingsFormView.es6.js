(function() {


const [readyPromise, resolve] = Promise.withResolver();


/**
 * A form for managing the settings of avatar services.
 *
 * This form lets you select the avatar service you wish to use, as well as
 * configure the settings for that avatar service.
 */
Djblets.Avatars.SettingsFormView = Backbone.View.extend({
    events: {
        'change #id_avatar_service_id': '_onServiceChanged',
        'submit': '_onSubmit'
    },

    /**
     * Initialize the form.
     */
    initialize() {
        console.assert(Djblets.Avatars.SettingsFormView.instance === null);
        Djblets.Avatars.SettingsFormView.instance = this;
        this._configForms = new Map();

        this._$config = this.$('.avatar-service-configuration');

        const services = this.model.get('services');
        this.listenTo(this.model, 'change:serviceID',
                      () => this._showHideForms());

        /*
         * The promise continuations will only be executed once the stack is
         * unwound.
         */
        resolve();
    },

    /**
     * Validate the current form upon submission.
     *
     * Args:
     *     e (Event):
     *         The form submission event.
     */
    _onSubmit(e) {
        const serviceID = this.model.get('serviceID');
        const currentForm = this._configForms.get(serviceID);

        if (currentForm && !currentForm.validate()) {
            e.preventDefault();
        }
    },

    /**
     * Render the child forms.
     *
     * This will show the for the currently selected service if it has one.
     *
     * Returns:
     *     Djblets.Avatars.SettingsFormView:
     *     This view (for chaining).
     */
    renderForms() {
        for (const form of this._configForms.values()) {
            form.render();
        }

        /*
         * Ensure that if the browser sets the value of the <select> upon
         * refresh that we update the model accordingly.
         */
        this.$('#id_avatar_service_id').change();
        this._showHideForms(true);

        return this;
    },

    /**
     * Show or hide the configuration form.
     */
    _showHideForms() {
        const services = this.model.get('services');
        const serviceID = this.model.get('serviceID');
        const currentForm = this._configForms.get(serviceID);
        const previousID = this.model.previous('serviceID');
        const previousForm = previousID
            ? this._configForms.get(previousID)
            : undefined;

        if (previousForm && currentForm) {
            previousForm.$el.hide();
            currentForm.$el.show();
        } else if (previousForm) {
            previousForm.$el.hide();
            this._$config.hide();
        } else if (currentForm) {
            currentForm.$el.show();
            this._$config.show();
        }

    },

    /**
     * Handle the service being changed.
     *
     * Args:
     *     e (Event):
     *         The change event.
     */
    _onServiceChanged(e) {
        const $target = $(e.target);
        this.model.set('serviceID', $target.val());
    }
}, {
    /**
     * The form instance.
     */
    instance: null,

    /**
     * Add a configuration form to the instance.
     *
     * Args:
     *     serviceID (string):
     *         The unique ID for the avatar service.
     *
     *     formClass (constructor):
     *         The view to use for the form.
     */
    addConfigForm(serviceID, formClass) {
        Djblets.Avatars.SettingsFormView.instance._configForms.set(
            serviceID,
            new formClass({
                el: $(`[data-avatar-service-id="${serviceID}"]`),
                model: Djblets.Avatars.SettingsFormView.instance.model
            }));
    },

    /**
     * A promise that is resolved when the avatar services form has been
     * initialized.
     */
    ready: readyPromise
});


})();
