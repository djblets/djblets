/**
 * Class for defining a hook point for extension hooks.
 */

import { BaseModel, spina } from '@beanbag/spina';

import { type ExtensionHook } from './extensionHookModel';


/**
 * Defines a point where extension hooks can plug into.
 *
 * This is meant to be instantiated and provided as a 'hookPoint' field on
 * an ExtensionHook subclass, in order to provide a place to hook into.
 */
@spina
export class ExtensionHookPoint extends BaseModel {
    /**********************
     * Instance variables *
     **********************/

    /**
     * A list of all hooks registered on this extension point.
     */
    hooks: ExtensionHook[];

    /**
     * Initialize the hook point.
     */
    initialize() {
        this.hooks = [];
    }

    /**
     * Add a hook instance to the list of known hooks.
     *
     * Args:
     *     hook (Djblets.ExtensionHook):
     *         The hook instance.
     */
    addHook(hook: ExtensionHook) {
        this.hooks.push(hook);
    }
}
