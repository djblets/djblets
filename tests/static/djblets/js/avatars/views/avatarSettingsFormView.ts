/**
 * A form for managing the settings of avatar services.
 */

import { BaseView, spina } from '@beanbag/spina';

import { type Settings } from '../models/avatarSettingsModel';
import { type ServiceSettingsFormView } from './avatarServiceSettingsFormView';


let resolveReady;
const readyPromise: Promise<void> = new Promise((resolve, reject) => {
    resolveReady = resolve;
});


/**
 * A form for managing the settings of avatar services.
 *
 * This form lets you select the avatar service you wish to use, as well as
 * configure the settings for that avatar service.
 */
@spina
export class SettingsFormView extends BaseView<Settings> {
    static events = {
        'change #id_avatar_service_id': '_onServiceChanged',
        'submit': '_onSubmit',
    };

    static instance: SettingsFormView = null;
    static ready: Promise<void> = readyPromise;

    /**********************
     * Instance variables *
     **********************/

    _configForms: Map<string, ServiceSettingsFormView>;

    _$config: JQuery;

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
    static addConfigForm(
        serviceID: string,
        formClass: typeof ServiceSettingsFormView,
    ) {
        SettingsFormView.instance._configForms.set(
            serviceID,
            new formClass({
                el: $(`[data-avatar-service-id="${serviceID}"]`),
                model: SettingsFormView.instance.model,
            }));
    }

    /**
     * Initialize the form.
     */
    initialize() {
        console.assert(SettingsFormView.instance === null);
        SettingsFormView.instance = this;
        this._configForms = new Map();

        this._$config = this.$('.avatar-service-configuration');

        this.listenTo(this.model, 'change:serviceID',
                      () => this._showHideForms());

        /*
         * The promise continuations will only be executed once the stack is
         * unwound.
         */
        resolveReady();
    }

    /**
     * Validate the current form upon submission.
     *
     * Args:
     *     e (Event):
     *         The form submission event.
     */
    _onSubmit(e: Event) {
        const serviceID = this.model.get('serviceID');
        const currentForm = this._configForms.get(serviceID);

        if (currentForm && !currentForm.validate()) {
            e.preventDefault();
        }
    }

    /**
     * Render the child forms.
     *
     * This will show the for the currently selected service if it has one.
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
        this._showHideForms();
    }

    /**
     * Show or hide the configuration form.
     */
    _showHideForms() {
        const serviceID = this.model.get('serviceID');
        const currentForm = this._configForms.get(serviceID);
        const previousID = this.model.previous('serviceID');
        const previousForm = previousID
            ? this._configForms.get(previousID)
            : undefined;

        if (previousForm && currentForm) {
            previousForm.hide();
            currentForm.show();
        } else if (previousForm) {
            previousForm.hide();
            this._$config.hide();
        } else if (currentForm) {
            currentForm.show();
            this._$config.show();
        }
    }

    /**
     * Handle the service being changed.
     *
     * Args:
     *     e (Event):
     *         The change event.
     */
    _onServiceChanged(e: Event) {
        const $target = $(e.target);
        const serviceID = $target.val() as string;

        this.model.set('serviceID', serviceID);
    }
}
