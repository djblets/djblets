/**
 * A set of configured conditions, and available choices.
 *
 * This tracks all the conditions that are being configured, handling assigning
 * each one an ID and tracking their state. It also provides information on
 * each choice available for a condition.
 *
 * Attributes:
 *     choices (Backbone.Collection):
 *         A collection of possible choices for a condition. Each entry is a
 *         :js:class:`Djblets.Forms.ConditionChoice`.
 *
 *     conditions (Backbone.Collection):
 *         A collection of configured conditions. Each entry is a
 *         :js:class:`Djblets.Forms.Condition`.
 *
 * Model Attributes:
 *     fieldName (string):
 *         The name of the form field for the main conditions element.
 *
 *     lastID (number):
 *         The last condition row ID used.
 */
Djblets.Forms.ConditionSet = Backbone.Model.extend({
    defaults: {
        fieldName: null,
        lastID: null
    },

    /**
     * Initialize the model.
     *
     * Args:
     *     attributes (object):
     *         Attribute values passed to the constructor.
     */
    initialize(attributes) {
        this.choices = new Backbone.Collection(attributes.choicesData, {
            model: Djblets.Forms.ConditionChoice,
            parse: true
        });

        this.conditions = new Backbone.Collection(attributes.conditionsData, {
            model: (attrs, options) => {
                const choice = attrs.choice ||
                               this.choices.get(attrs.choiceID);
                const operator = attrs.operator ||
                                 (choice
                                  ? choice.operators.get(attrs.operatorID)
                                  : null);
                const lastID = this.get('lastID');
                const conditionID = (lastID === null ? 0 : lastID + 1);

                this.set('lastID', conditionID);

                return new Djblets.Forms.Condition(
                    {
                        id: conditionID,
                        choice: choice,
                        operator: operator,
                        value: attrs.value,
                        valid: attrs.valid,
                        error: attrs.error
                    },
                    options);
            }
        });
    },

    /**
     * Add a new condition.
     *
     * This will construct a new condition with defaults and add it to the
     * collection.
     */
    addNewCondition() {
        const choice = this.choices.first();

        this.conditions.add({
            choice: choice,
            operator: choice.operators.first()
        });
    },

    /**
     * Parse the attribute data passed to the model.
     *
     * This will extract only the ``fieldName`` attribute, leaving the rest
     * to be specially handled by :js:func:`initialize`.
     *
     * Args:
     *     data (object):
     *         The attribute data passed to the model.
     *
     * Returns:
     *     object:
     *     The parsed attributes.
     */
    parse(data) {
        return {
            fieldName: data.fieldName
        };
    }
});
