(function() {


const ParentView = Djblets.Forms.BaseConditionValueFieldView;


/**
 * Provides an HTML form input element for capturing a value for a condition.
 *
 * This can be used with any standard HTML form element that works with
 * jQuery's :js:func:`jQuery.val`. The form element must be the top-most
 * element defined in ``fieldHTML``.
 */
Djblets.Forms.ConditionValueFormFieldView = ParentView.extend({
    /**
     * Render the value field.
     *
     * Returns:
     *     Djblets.Forms.ConditionValueFormFieldView:
     *     The instance, for chaining.
     */
    render() {
        ParentView.prototype.render.call(this);

        this.$input = this.$el.children()
            .attr('name', this.model.get('fieldName'));

        return this;
    },

    /**
     * Set a new value for the field.
     *
     * Args:
     *     value (object):
     *         The new value to set.
     */
    setValue(value) {
        this.$input.val(value);
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
    getValue(value) {
        return this.$input.val();
    }
});


})();
