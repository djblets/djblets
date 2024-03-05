/**
 * A base class for avatar service settings forms.
 */

import { BaseView, spina } from '@beanbag/spina';


/**
 * A base class for avatar service settings forms.
 *
 * Subclasses should override this to provide additional behaviour for
 * previews, etc.
 */
@spina
export class ServiceSettingsFormView extends BaseView {
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
}
