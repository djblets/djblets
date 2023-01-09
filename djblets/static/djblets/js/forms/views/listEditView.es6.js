(function() {


const entryTemplate = _.template(dedent`
    <li class="djblets-c-list-edit-widget__entry"
        data-list-index="<%- index %>">
      <%= renderedDefaultRow %>
     <a href="#" class="djblets-c-list-edit-widget__remove-item"
        role="button" title="<%- removeText %>">
       <span class="fa fa-times"></span>
     </a>
    </li>
`);

/**
 * A view for editing a list of elements.
 *
 * This is the JavaScript view for
 * :py:class:`djblets.forms.widgets.ListEditWidget`.
 */
Djblets.Forms.ListEditView = Backbone.View.extend({
    events: {
        'click .djblets-c-list-edit-widget__add-item': '_addItem',
        'click .djblets-c-list-edit-widget__remove-item': '_removeItem',
    },

    /**
     * Initialize the view.
     *
     * Version Changed:
     *     3.0:
     *     * Removed the `inputAttrs` option.
     *     * Removed the `sep` option.
     *     * Added the `fieldName` option.
     *     * Added the `renderedDefaultRow` option.
     *
     * Args:
     *     options (object):
     *         The view options.
     *
     * Option Args:
     *     removeText (string):
     *         The localized text for removing an item.
     *
     *     fieldName (string):
     *         The form field name corresponding to this ListEditWidget.
     *
     *     renderedDefaultRow (string):
     *         The HTML for a default item in the list. This is used to
     *         render a default item when adding a new item to the list.
     */
    initialize(options) {
        this._removeText = options.removeText;
        this._fieldName = options.fieldName;
        this._renderedDefaultRow = options.renderedDefaultRow;
        this._numItems = 0;

    },

    /**
     * Render the view.
     *
     * Since most of the view is rendered by Django, this just sets up some
     * event listeners.
     *
     * Returns:
     *     Djblets.Forms.ListEditView:
     *     This view.
     */
    render() {
        this.$el.data('djblets-list-edit-view', this);

        this._$list = this.$el.children(
            '.djblets-c-list-edit-widget__entries');
        this._numItems =
            this._$list.find('.djblets-c-list-edit-widget__entry').length;
        $(`input[name="${this._fieldName}_num_rows"]`).val(this._numItems);
        this._$addBtn = this.$el.children(
            '.djblets-c-list-edit-widget__add-item');

        return this;
    },

    /**
     * Create and format the HTML for a new entry in the list.
     *
     * Args:
     *     index (int):
     *         The index of the new entry in the list of entries.
     *
     * Returns:
     *     jQuery:
     *     The HTML for the new entry in the list.
     */
    _createDefaultEntry(index) {
        const $entry = $(entryTemplate({
            index: index,
            removeText: this._removeText,
            renderedDefaultRow: this._renderedDefaultRow,
        }));
        this._updateEntryInputName($entry, index);

        $(`input[name="${this._fieldName}_num_rows"]`).val(index+1);
        $entry.find('.djblets-c-list-edit-widget__add-item')
            .on('click', e => this._addItem(e));

        return $entry;
    },

    /**
     * Update the name(s) of the entry's .djblets-c-list-edit-widget__input(s)
     * so that they contain the appropriate index for the entry.
     *
     * Args:
     *     $entry (jQuery):
     *         The entry to update.
     *
     *     index (int):
     *         The index of the entry in the list of entries.
     */
    _updateEntryInputName($entry, index) {
        const $inputs = $entry.find('.djblets-c-list-edit-widget__input');

        // The entry may have more than one "input".
        if ($inputs.length > 1) {
            $inputs.each((idx, el) =>
                $(el).attr('name',
                           `${this._fieldName}_value[${index}]_${idx}`));
        } else {
            $inputs.attr('name', `${this._fieldName}_value[${index}]`);
        }
    },

    /**
     * Add an item to the list.
     *
     * Args:
     *     e (Event):
     *         The click event that triggered this event handler.
     */
    _addItem(e) {
        e.preventDefault();
        e.stopPropagation();

        this._$list.append(this._createDefaultEntry(this._numItems));
        this._numItems += 1;
    },

    /**
     * Remove an item.
     *
     * When there is only a single item in the list, we clear it instead of
     * removing it so there is always at least one item in the list.
     *
     * Args:
     *     e (Event):
     *         The click event that triggered this event handler.
     */
    _removeItem(e) {
        e.preventDefault();
        e.stopPropagation();

        const $target = $(e.target);
        const $entry = $target.closest('.djblets-c-list-edit-widget__entry');

        if (this._numItems > 1) {
            $entry.remove();
            this._numItems -= 1;
            this._$list.find('.djblets-c-list-edit-widget__entry')
                .each((idx, el) => {
                    const $el = $(el);
                    $el.attr('data-list-index', idx);
                    this._updateEntryInputName($el, idx);
                });
            $(`input[name="${this._fieldName}_num_rows"]`)
                .val(this._numItems);
        } else {
            const $defaultEntry = this._createDefaultEntry(0);
            $entry.replaceWith($defaultEntry);
        }
    },
});


})();
