/**
 * A base class for avatar service settings forms.
 */

import {
    type BaseModel,
    BaseView,
    spina,
} from '@beanbag/spina';


/**
 * A base class for avatar service settings forms.
 *
 * Subclasses should override this to provide additional behaviour for
 * previews, etc.
 */
@spina
export class ServiceSettingsFormView extends BaseView<
    BaseModel,
    HTMLFieldSetElement
> {
    /**
     * Validate the form.
     *
     * Returns:
     *     boolean:
     *     Whether or not the form is valid.
     */
    validate(): boolean {
        return true;
    }

    /**
     * Hide the form.
     *
     * This will set the disabled and hidden states.
     *
     * Version Changed:
     *     5.0:
     *     This no longer alters the ``display`` state of the element.
     *
     * Returns:
     *     ServiceSettingsFormView:
     *     This object, for chaining.
     */
    hide(): this {
        const el = this.el;
        el.disabled = true;
        el.hidden = true;

        return this;
    }

    /**
     * Show the form.
     *
     * This will remove the disabled and hidden states.
     *
     * Version Changed:
     *     5.0:
     *     This no longer alters the ``display`` state of the element.
     *
     * Returns:
     *     ServiceSettingsFormView:
     *     This object, for chaining.
     */
    show(): this {
        const el = this.el;
        el.disabled = false;
        el.hidden = false;

        return this;
    }
}
