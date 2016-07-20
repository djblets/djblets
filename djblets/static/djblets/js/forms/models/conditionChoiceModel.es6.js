/**
 * A possible choice for a condition.
 *
 * This represents a single choice for a condition, such as a summary or list of
 * objects, that a condition processor will inspect and match against
 * configurations. A condition contains a list of possible operators (such as
 * "Is," "Is not," "Starts with," etc.) and a field for handling any values
 * for the choice and operator.
 *
 * Attributes:
 *     operators (Backbone.Collection):
 *         A collection of operators that are valid for this condition. Each
 *         entry is a :js:class:`Djblets.Forms.ConditionOperator`.
 *
 * Model Attributes:
 *     name (string):
 *         The name of the condition. This is what will be displayed to the
 *         user.
 *
 *     valueField (object):
 *         Information about the object handling the storage and manipulation
 *         of values for the condition. This will be the default value field
 *         for all operators on the choice, but operators can provide their own.
 *
 *         This will have ``modelClass` and ``viewClass`` keys pointing to the
 *         object constructors for the model and view for the value field,
 *         along with ``modelData`` and ``viewData`` controlling the model
 *         attributes and view options, respectively.
 */
Djblets.Forms.ConditionChoice = Backbone.Model.extend({
    defaults: {
        name: null,
        valueField: null
    },

    /**
     * Initialize the choice.
     *
     * Attributes:
     *     operators (Array):
     *         The list of operators to populate the operators collection.
     */
    initialize(attributes) {
        this.operators = new Backbone.Collection(attributes.operators, {
            model: Djblets.Forms.ConditionOperator,
            parse: true
        });
    },

    /**
     * Create the value field for the choice.
     *
     * This will construct a new instance of the view used to take values for
     * this choice.
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
            valueField: Djblets.Forms.ConditionChoice.parseValueFieldData(
                data.valueField)
        };
    }
}, {
    /**
     * Parse value field data into a standard structure.
     *
     * This can be used by any choice-related class that needs to deal with
     * value fields. It's intended for internal use only.
     *
     * Args:
     *     data (object):
     *         The value field data to parse.
     *
     * Returns:
     *     dict:
     *     The resulting value field information, or ``null`` if the data
     *     provided is ``undefined``.
     */
    parseValueFieldData(data) {
        let valueField = null;

        if (data !== undefined) {
            const fieldModelInfo = data.model;
            const fieldViewInfo = data.view;

            valueField = {
                modelClass: Djblets.getObjectByName(fieldModelInfo.className),
                modelData: fieldModelInfo.data,
                viewClass: Djblets.getObjectByName(fieldViewInfo.className),
                viewData: fieldViewInfo.data
            };
        }

        return valueField;
    }
});
