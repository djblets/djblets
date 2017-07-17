/**
 * Base class for an item in a list for config forms.
 *
 * ListItems provide text representing the item, optionally linked. They
 * can also provide zero or more actions that can be invoked on the item
 * by the user.
 *
 * Model Attributes:
 *     canRemove (boolean):
 *         Whether or not the model can be removed.
 *
 *     editURL (string):
 *         The URL to edit the model.
 *
 *     loading (boolean):
 *         Whether or not the model is loading content from the server.
 *
 *     removeLabel (string):
 *         The label for the ``remove`` action.
 *
 *     showRemove (boolean):
 *         Whether or not the ``remove`` action should be present.
 *
 *         If the model is instantiated with this property ``true``, the
 *         :js:attr:`actions` attribute will be pre-populated with an action
 *         to remove itself.
 *
 *     text (string):
 *         The display name of the model.
 *
 * Attributes:
 *     actions (array):
 *         The actions available for this item. Actions are objects with the
 *         following attribtues:
 *
 *         ``children`` (:js:class:`array`, optional):
 *             An array of actions, each of which is an :js:class:`object` with
 *             these same attributes.
 *
 *         ``danger`` (:js:class:`boolean`, optional):
 *             When ``true``, this attributes indicates that the action will
 *             cause permanent, undoable damage. This is only useful for
 *             button actions.
 *
 *             If this attribute is present, the action will be rendered as a
 *             menu and its children will be rendered as items in that menu.
 *
 *         ``enabled`` (:js:class:`boolean`):
 *             Whether or not the action will be enabled.
 *
 *         ``iconName`` (:js:class:`string`, optional):
 *             The name of the icon to display to the action, if any. This
 *             is the :samp:`{iconname}` part of :samp:`rb-icon-{iconname}`.
 *
 *         ``id`` (:js:class:`string` or :js:class:`number`):
 *             A unique identifier for the action. It is used when registering
 *             action handlers and will also be appended to the class name for
 *             the action.
 *
 *         ``label`` (:js:class:`string`):
 *             The action's label.
 *
 *         ``propName`` (:js:class:`string`, optional):
 *             For a checkbox action, this attribute specifies the attribute on
 *             the model that will be set to reflect the checkbox's state.
 *
 *         ``type`` (:js:class:`string`, optional):
 *             The type of the action. If provided, it can have the following
 *             values:
 *
 *             ``'checkbox'``:
 *                 The action will be rendered as a checkox.
 *
 *             ``'radio'``:
 *                 The action will be rendered as a radio button.
 *
 *             Otherwise the action will be rendered as a button.
 */
Djblets.Config.ListItem = Backbone.Model.extend({
    defaults: {
        text: null,
        editURL: null,
        showRemove: false,
        canRemove: true,
        loading: false,
        removeLabel: gettext('Remove')
    },

    /**
     * Initialize the item.
     *
     * If showRemove is true, this will populate a default Remove action
     * for removing the item.
     *
     * Args:
     *     options (object, optional):
     *         The model options.
     *
     * Option Args:
     *     actions (list of object):
     *         A list of actions to add to the item.
     */
    initialize(options={}) {
        this.actions = options.actions || [];

        if (this.get('showRemove')) {
            this.actions.push({
                id: 'delete',
                label: this.get('removeLabel'),
                danger: true,
                enabled: this.get('canRemove')
            });
        }
    },
});
