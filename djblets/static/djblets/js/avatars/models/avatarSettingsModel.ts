/**
 * Settings for the avatar configuration form.
 */

import {
    type ModelAttributes,
    BaseModel,
    spina,
} from '@beanbag/spina';


/**
 * Attributes for the Settings model.
 *
 * Version Added:
 *     5.0
 */
export interface SettingsAttributes extends ModelAttributes {
    /**
     * A mapping of each service ID to its configuration object.
     */
    configuration: { [key: string]: object };

    /**
     * The currently selected service ID.
     */
    serviceID: string;

    /**
     * A mapping of each service ID to its properties.
     */
    services: { [key: string]: object };
}


/**
 * Settings for the avatar configuration form.
 */
@spina
export class Settings extends BaseModel<SettingsAttributes> {
    /**
     * Return defaults for the model attributes.
     *
     * Returns:
     *     SettingsAttributes:
     *     Default values for the model attributes.
     */
    static defaults(): SettingsAttributes {
        return {
            configuration: {},
            serviceID: null,
            services: {},
        };
    }
}
