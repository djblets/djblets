/**
 * Base view for capturing a value for a condition.
 *
 * This is meant to be subclassed, and subclasses must implement
 * :js:func:`setValue` and :js:func:`getValue`.
 */
Djblets.Forms.BaseConditionValueFieldView = Backbone.View.extend({
    tagName: 'span',

    /**
     * Render the value field.
     *
     * By default, this will render the ``fieldHTML`` attribute of the model
     * to HTML and set it for the view's element. Subclasses can override this
     * to perform additional rendering logic.
     *
     * Returns:
     *     Djblets.Forms.BaseConditionValueFieldView:
     *     The instance, for chaining.
     */
    render() {
        this.$el.html(this.model.get('fieldHTML'));

        return this;
    },

    /**
     * Set a new value for the field.
     *
     * This must be implemented by subclasses.
     *
     * Args:
     *     value (object):
     *         The new value to set.
     */
    setValue(value) {
        console.assert(false,
                       'setValue() must be implemented by this subclass.');
    },

    /**
     * Return the current value for the field.
     *
     * This must be implemented by subclasses.
     *
     * Returns:
     *     object:
     *     The field's current value.
     */
    getValue() {
        console.assert(false,
                       'getValue() must be implemented by this subclass.');
    }
});
