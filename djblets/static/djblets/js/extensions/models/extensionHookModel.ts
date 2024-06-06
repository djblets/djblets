/**
 * Base support for defining extension hooks.
 */

import {
    type ModelAttributes,
    BaseModel,
    spina,
} from '@beanbag/spina';

import { type ExtensionHookPoint } from './extensionHookPointModel';
import { type Extension } from './extensionModel';


/**
 * Attributes that can be passed to an extension hook's constructor.
 *
 * Version Added:
 *     4.0
 */
export interface ExtensionHookAttrs extends ModelAttributes {
    /**
     * The extension that owns this hook.
     */
    extension: Extension;
}


/**
 * Base class for hooks that an extension can use to augment functionality.
 *
 * Each type of hook represents a point in the codebase that an extension
 * is able to plug functionality into.
 *
 * Subclasses are expected to set a hookPoint field in the prototype to an
 * instance of ExtensionPoint.
 *
 * Instances of an ExtensionHook subclass that extensions create will be
 * automatically registered with both the extension and the list of hooks
 * for that ExtensionHook subclass.
 *
 * Callers that use ExtensionHook subclasses to provide functionality can
 * use the subclass's each() method to loop over all registered hooks.
 */
@spina({
    prototypeAttrs: [
        'each',
        'hookPoint',
    ],
})
export class ExtensionHook<
    TDefaults extends ExtensionHookAttrs = ExtensionHookAttrs
> extends BaseModel<TDefaults> {
    /**
     * An ExtensionHookPoint instance.
     *
     * This must be defined and instantiated by a subclass of ExtensionHook,
     * but not by subclasses created by extensions.
     */
    static hookPoint: ExtensionHookPoint = null;
    hookPoint: ExtensionHookPoint;

    static defaults: ExtensionHookAttrs = {
        extension: null,
    };

    /**
     * Loop through each registered hook instance and call the given callback.
     *
     * Args:
     *     cb (function):
     *         The callback to call.
     *
     *     context (object, optional):
     *         Optional context to use when calling the callback.
     */
    static each(
        cb: (ExtensionHook) => void,
        context: unknown = null,
    ) {
        for (const hook of this.prototype.hookPoint.hooks) {
            cb.call(context, hook);
        }
    }

    /**
     * Initialize the hook.
     *
     * This will add the instance of the hook to the extension's list of
     * hooks, and to the list of known hook instances for this hook point.
     *
     * After initialization, setUpHook will be called, which a subclass
     * can use to provide additional setup.
     */
    initialize() {
        const extension = this.get('extension');

        console.assert(
            !!this.hookPoint,
            'This ExtensionHook subclass must define hookPoint');
        console.assert(
            !!extension,
            'An Extension instance must be passed to ExtensionHook');

        extension.hooks.push(this);
        this.hookPoint.addHook(this);

        this.setUpHook();
    }

    /**
     * Set up additional state for the hook.
     *
     * This can be overridden by subclasses to provide additional
     * functionality.
     */
    setUpHook() {
        /* Empty by default. */
    }
}
