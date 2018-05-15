/**
 * Manages the display of a consent field.
 *
 * This helps style consent fields to better represent the current choice
 * made, altering labels and colors. It provides no functionality beyond
 * enhancing the look of the field beyond what can be done in CSS.
 */
Djblets.Forms.PrivacyConsentFieldView = Backbone.View.extend({
    events: {
        'change input': '_onConsentChanged',
    },

    /**
     * Initialize the view.
     */
    initialize() {
        const $choices = this.$('.privacy-consent-field-choices');
        const $allowChoice =
            $choices.find('.privacy-consent-field-choice-allow');
        const $blockChoice =
            $choices.find('.privacy-consent-field-choice-block');

        this._$allowInput = $allowChoice.children('input');
        this._$allowLabel = $allowChoice.children('label');
        this._$blockInput = $blockChoice.children('input');
        this._$blockLabel = $blockChoice.children('label');
    },

    /**
     * Render the view.
     *
     * Returns:
     *     Djblets.Forms.PrivacyConsentFieldView:
     *     This view, for chaining.
     */
    render() {
        this._onConsentChanged();

        return this;
    },

    /**
     * Handler for when the consent choice has changed.
     *
     * This will toggle classes on the field's element to reflect the
     * current consent choice, and update the labels.
     */
    _onConsentChanged() {
        const allowed = this._$allowInput.is(':checked');
        const blocked = this._$blockInput.is(':checked');

        this.$el.toggleClass('privacy-consent-field-allow', allowed);
        this.$el.toggleClass('privacy-consent-field-block', blocked);

        this._$allowLabel.text(allowed
                               ? gettext('Allowed')
                               : gettext('Allow'));
        this._$blockLabel.text(blocked
                               ? gettext('Blocked')
                               : gettext('Block'));
    },
});
