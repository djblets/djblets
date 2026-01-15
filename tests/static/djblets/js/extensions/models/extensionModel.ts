/**
 * Base class for an extension.
 */

import {
    BaseModel,
    ModelAttributes,
    spina,
} from '@beanbag/spina';

import { type ExtensionHook } from './extensionHookModel';


/**
 * Attributes that can be passed to an extension's constructor.
 *
 * Version Added:
 *     4.0
 */
export interface BaseExtensionAttrs extends ModelAttributes {
    /**
     * The unique ID of the extension.
     */
    id: string;

    /**
     * The display name of the extension.
     */
    name: string;

    /**
     * A mapping of settings made available to the extension.
     */
    settings: {
        [key: string]: unknown,
    }
}


/**
 * Base class for an extension.
 *
 * Extensions that deal with JavaScript should subclass this to provide any
 * initialization code it needs, such as the initialization of hooks.
 *
 * Extension instances will have read access to the server-stored settings
 * for the extension.
 */
@spina
export class Extension<
    TDefaults extends BaseExtensionAttrs = BaseExtensionAttrs
> extends BaseModel<TDefaults> {
    static defaults: BaseExtensionAttrs = {
        id: null,
        name: null,
        settings: {},
    };

    /**********************
     * Instance variables *
     **********************/

    /**
     * The list of extension hooks added by this extension.
     *
     * This is automatically populated when instantiating extension hooks.
     */
    hooks: ExtensionHook[];

    /**
     * Initialize the extension.
     *
     * Subclasses that override this are expected to call this method.
     */
    initialize() {
        this.hooks = [];
    }
}
