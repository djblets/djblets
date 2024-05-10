/**
 * Base class for an item in a list for config forms.
 */

import {
    type ModelAttributes,
    BaseModel,
    spina,
} from '@beanbag/spina';


/**
 * Attributes for the ListItem model.
 *
 * Version Added:
 *     4.0
 */
export interface ListItemAttrs extends ModelAttributes {
    /** Whether or not the model can be removed. */
    canRemove?: boolean;

    /** The URL to edit the model. */
    editURL?: string;

    /**
     * A string representing the item's state.
     *
     * This is used for those items that need to show an enabled, disabled,
     * error, or custom state.
     */
    itemState?: string;

    /** Whether or not the model is loading content from the server. */
    loading?: boolean;

    /** The label for the "remove" action. */
    removeLabel?: string;

    /**
     * Whether or not the "remove" action should be present.
     *
     * If the model is instantiated with this property set to ``true``, the
     * :js:attr:`actions` attribute will be pre-propulated with an action to
     * remove itself.
     */
    showRemove?: boolean;

    /** The display name of the model. */
    text?: string;
}


/**
 * An action for a list item.
 *
 * Version Added:
 *     4.0
 */
export interface ListItemAction {
    /**
     * The ARIA label to assign to the element.
     */
    ariaLabel?: string;

    /**
     * An array of child actions.
     *
     * If this attribute is present, the action will be rendered as a menu and
     * its children will be rendered as items in that menu.
     */
    children?: ListItemAction[];

    /**
     * Whether the action will cause permanent data loss or damage.
     *
     * This is only useful for button actions.
     */
    danger?: boolean;

    /**
     * Whether the action is enabled.
     *
     * This defaults to ``true``.
     */
    enabled?: boolean;

    /**
     * The name of the property on the model to bind the enabled state to.
     */
    enabledPropName?: string;

    /**
     * Whether to inverse the enabled state when binding enabledPropName.
     *
     * This defaults to ``false``.
     */
    enabledPropInverse?: boolean;

    /**
     * Whether to dispatch a click event when toggled on.
     *
     * This only applies to radio button actions.
     *
     * This defaults to ``false``.
     */
    dispatchOnClick?: boolean;

    /**
     * The name of the icon to display for the action, if any.
     *
     * This is the :samp:`{iconname}` part of :samp:`rb-icon-{iconname}`.
     */
    iconName?: string;

    /**
     * A unique identifier for the action.
     *
     * This is used when registering action handlers, and is also appended to
     * the class name for the action element.
     */
    id: string | number;

    /** The action's label. */
    label: string;

    /** The name to assign to the action's element. */
    name?: string;

    /**
     * Whether this is a primary action for the item.
     *
     * This is only useful for button actions.
     */
    primary?: boolean;

    /**
     * The property name to reflect this action.
     *
     * For checkbox actions, this is used to map a model attribute to the
     * checkbox state.
     */
    propName?: string;

    /**
     * The type of the action.
     *
     * This may have the following values:
     *
     * ``'checkbox'``:
     *     The action will be rendered as a checkbox.
     *
     * ``'radio'``:
     *     The action will be rendered as a radio button.
     *
     * For all other values, or if not specified, the action will render as a
     * button.
     */
    type?: string;

    /**
     * A URL to link to for actions that should act as a link.
     *
     * This is only useful for button actions.
     */
    url?: string;
}


/**
 * Attributes for the ListItem constructor.
 *
 * This is a legacy type definition from when we had additional constructor
 * options.
 *
 * Version Changed:
 *     5.0:
 *     Removed the ``actions`` member.
 */
export type ListItemConstructorAttrs = ListItemAttrs;


/**
 * Base class for an item in a list for config forms.
 *
 * ListItems provide text representing the item, optionally linked. They
 * can also provide zero or more actions that can be invoked on the item
 * by the user.
 */
@spina
export class ListItem<
    TDefaults extends ListItemAttrs = ListItemAttrs,
    TExtraModelOptions = unknown,
    TModelOptions = Backbone.ModelSetOptions
> extends BaseModel<TDefaults, TExtraModelOptions, TModelOptions> {
    /** The default values for the model attributes. */
    static defaults: Partial<ListItemAttrs> = {
        canRemove: true,
        editURL: null,
        itemState: null,
        loading: false,
        removeLabel: _`Remove`,
        showRemove: false,
        text: null,
    };

    /**********************
     * Instance variables *
     **********************/

    /** The actions available for this item. */
    actions: ListItemAction[] = [];

    /**
     * A mapping of item states to text.
     *
     * Subclasses can extend this to provide custom strings, or support
     * custom item states.
     */
    itemStateTexts = {
        disabled: _`Disabled`,
        enabled: _`Enabled`,
        error: _`Error`,
    };

    /**
     * Initialize the item.
     *
     * If showRemove is true, this will populate a default Remove action
     * for removing the item.
     *
     * Args:
     *     attributes (ListItemAttrs, optional):
     *         Attributes for the model.
     */
    initialize(attributes: ListItemAttrs = {}) {
        console.assert(
            attributes.actions === undefined,
            dedent`
                Passing in actions to the Djblets.Config.ListItem constructor
                has been removed as of Djblets 5.0. Actions should be passed
                to the setActions() method instead.
            `);

        if (this.get('showRemove')) {
            this.actions.push({
                danger: true,
                enabled: this.get('canRemove'),
                id: 'delete',
                label: this.get('removeLabel'),
            });
        }
    }

    /**
     * Set the actions available for this item.
     *
     * Args:
     *     actions (Array of ListItemAction):
     *         The new action definitions.
     */
    setActions(actions: ListItemAction[]) {
        this.actions = actions;
        this.trigger('actionsChanged');
    }
}
