/**
 * A configured condition in a set.
 *
 * The condition represents a combination of a choice, operator, and value.
 * It's owned by a :js:class:`Djblets.Forms.ConditionSet`.
 *
 * Model Attributes:
 *     choice (Djblets.Forms.ConditionChoice):
 *         The selected choice for the condition.
 *
 *     error (string):
 *         An error message for this condition. This would be set if the
 *         user had invalid or missing data, submitted the form, and was
 *         then presented with a validation error.
 *
 *     operator (Djblets.Forms.ConditionOperator):
 *         The selected operator for the condition.
 *
 *     valid (boolean):
 *         Whether this condition is valid. A valid condition is one that
 *         could be loaded successfully (its choice and operator were
 *         registered). An invalid one is intended to be presented as-is,
 *         so the user can figure out what state things were in.
 *
 *     value (object):
 *         The value for the choice, or ``null`` if unset.
 */
Djblets.Forms.Condition = Backbone.Model.extend({
    defaults: {
        choice: null,
        error: null,
        operator: null,
        valid: true,
        value: null
    },

    /**
     * Initialize the condition.
     *
     * This will set up the condition and begin listening for changes to the
     * properties, setting sane defaults when the choice changes.
     */
    initialize() {
        /*
         * When the choice changes, we need to change the operator and value
         * as well. This must be done after the choice event handlers have
         * run, to give consumers a chance to deal with the new choice. The
         * 'change' signal is the only time to do this without deferring to
         * the next event loop (which makes testing harder).
         */
        this.on('change', () => {
            const choice = this.get('choice');

            if (choice !== this.previous('choice')) {
                /* Reset the operatorID to the first option for this choice. */
                this.set('operator', choice.operators.first());

                /*
                 * Now unset the value.
                 *
                 * Note that we're not doing this during operator change,
                 * because we don't want the user to lose all state if switching
                 * between operators. Ideally, we want to keep what they had. If
                 * the value won't be used, it simply won't be used, and if it
                 * can be used for multiple operators, we want to preserve it.
                 */
                this.unset('value');
            }
        });
    },

    /**
     * Destroy the condition.
     *
     * This will stop listening for events and emit a "destroy" signal, just
     * like the standard :js:class:`Backbone.Model.destroy`. Unlike the standard
     * method, no HTTP requests are made to a server.
     *
     * Args:
     *     options (object):
     *         Options passed to the method. These are directly provided to
     *         listeners of the ``destroy`` event, for compatibility with
     *         Backbone's method, and is otherwise not used.
     */
    destroy(options) {
        this.stopListening();
        this.trigger('destroy', this, this.collection, options);
    }
});
