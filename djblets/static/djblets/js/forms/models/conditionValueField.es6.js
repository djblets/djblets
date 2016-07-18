/**
 * A model for handling state and logic around condition values.
 *
 * By default, this simply provides basic attribute storage for any model data
 * provided by the Python class for the choice, and is otherwise no different
 * than :js:class:`Backbone.Model`. Subclasses can override this to provide
 * additional attribute handling or logic.
 *
 * Model Attributes:
 *     fieldHTML (string):
 *         The rendered HTML for the field.
 */
Djblets.Forms.ConditionValueField = Backbone.Model.extend({
    defaults: {
        fieldHTML: null
    }
});
