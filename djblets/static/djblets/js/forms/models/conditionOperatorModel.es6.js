/**
 * A possible operator for a condition choice.
 *
 * An operator simply stores state indicating the operator name, ID, and whether
 * the user should be prompted for a value.
 *
 * Model Attributes:
 *     name (string):
 *         The human-readable name of the operator.
 *
 *     useValue (boolean):
 *         Whether the user should be prompted for a value. Defaults to
 *         ``false``.
 *
 *     valueField (object):
 *         Information about the object handling the storage and manipulation
 *         of values for the condition. If set, it will override the default
 *         value for the condition.
 *
 *         This will have ``modelClass` and ``viewClass`` keys pointing to the
 *         object constructors for the model and view for the value field,
 *         along with ``modelData`` and ``viewData`` controlling the model
 *         attributes and view options, respectively.
 */
Djblets.Forms.ConditionOperator = Backbone.Model.extend({
    defaults: {
        name: null,
        useValue: false,
        valueField: null
    },

    /**
     * Create the value field for the operator.
     *
     * This will construct a new instance of the view used to take values for
     * this operator.
     *
     * Args:
     *     fieldName (string):
     *         The name for the form field.
     *
     * Returns:
     *     Djblets.Forms.BaseConditionValueFieldView:
     *     The view for the field.
     */
    createValueField(fieldName) {
        const valueField = this.get('valueField');

        console.assert(valueField,
                       'This operator does not have a custom valueField.');

        return new valueField.viewClass(_.defaults({
            model: new valueField.modelClass(_.defaults({
                fieldName: fieldName
            }, valueField.modelData))
        }, valueField.viewData));
    },

    /**
     * Parse the attribute data passed to the model.
     *
     * Args:
     *     data (object):
     *         The attribute data passed to the model.
     *
     *  Returns:
     *     object:
     *     The parsed attributes.
     */
    parse(data) {
        return {
            id: data.id,
            name: data.name,
            useValue: data.useValue,
            valueField: Djblets.Forms.ConditionChoice.parseValueFieldData(
                data.valueField)
        };
    }
});
