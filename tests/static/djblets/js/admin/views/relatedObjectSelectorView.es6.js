/**
 * A widget to select related objects using search and autocomplete.
 *
 * This is particularly useful for models where there can be a ton of rows in
 * the database. The built-in admin widgets provide a pretty poor
 * experience--either populating the list with the entire contents of the
 * table, which is super slow, or just listing PKs, which isn't usable.
 */
Djblets.RelatedObjectSelectorView = Backbone.View.extend({
    className: 'related-object-selector',

    /** Whether to automatically add a close action to selected options. */
    autoAddClose: true,

    /** The tag name to use for selected options. */
    optionTagName: 'li',

    /**
     * The search placeholder text.
     *
     * Subclasses should override this.
     */
    searchPlaceholderText: '',

    /**
     * The element template.
     *
     * Subclasses may override this to change rendering.
     */
    template: _.template(dedent`
        <select placeholder="<%- searchPlaceholderText %>"
                class="related-object-options"></select>
        <% if (multivalued) { %>
        <ul class="related-object-selected"></ul>
        <% } %>
    `),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     $input (jQuery):
     *         The ``<input>`` element which should be populated with the list
     *         of selected item PKs.
     *
     *     initialOptions (Array of object):
     *         The initially selected options.
     *
     *     multivalued (boolean):
     *         Whether or not the widget should allow selecting multiple
     *         values.
     *
     *     selectizeOptions (object):
     *          Additional options to pass in to $.selectize.
     */
    initialize(options) {
        this.options = options;
        this._$input = options.$input;
        this._selectizeOptions = options.selectizeOptions;
        this._selectedIDs = new Map();

        _.bindAll(this, 'renderOption');
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.RelatedObjectSelectorView:
     *     This object, for chaining.
     */
    render() {
        const self = this;

        this.$el.html(this.template({
            multivalued: this.options.multivalued,
            searchPlaceholderText: this.searchPlaceholderText,
        }));

        this._$selected = this.$('.related-object-selected');

        const renderItem = this.options.multivalued
                           ? () => ''
                           : this.renderOption;

        const selectizeOptions = _.defaults(this._selectizeOptions, {
            copyClassesToDropdown: true,
            dropdownParent: 'body',
            preload: 'focus',

            render: {
                item: renderItem,
                option: this.renderOption,
            },

            load(query, callback) {
                self.loadOptions(
                    query,
                    data => callback(data.filter(
                        item => !self._selectedIDs.has(item.id)
                    ))
                );
            },

            onChange(selected) {
                if (selected) {
                    self._onItemSelected(this.options[selected], true);

                    if (self.options.multivalued) {
                        this.removeOption(selected);
                    }
                }

                if (self.options.multivalued) {
                    this.clear();
                }
            },
        });

        if (!this.options.multivalued && this.options.initialOptions.length) {
            const item = this.options.initialOptions[0];
            selectizeOptions.options = this.options.initialOptions;
            selectizeOptions.items = [item[selectizeOptions.valueField]];
        }

        this.$('select').selectize(selectizeOptions);

        if (this.options.multivalued) {
            this.options.initialOptions.forEach(
                item => this._onItemSelected(item, false)
            );
        }

        this._$input.after(this.$el);

        return this;
    },

    /**
     * Update the "official" ``<input>`` element.
     *
     * This copies the list of selected item IDs into the form field which will
     * be submitted.
     */
    _updateInput() {
        this._$input.val(Array.from(this._selectedIDs.keys()).join(','));
    },

    /**
     * Callback for when an item is selected.
     *
     * Args:
     *     item (object):
     *         The newly-selected item.
     *
     *     addToInput (boolean):
     *         Whether the ID of the item should be added to the ``<input>``
     *         field.
     *
     *         This will be ``false`` when populating the visible list from the
     *         value of the form field when the page is initially loaded, and
     *         ``true`` when adding items interactively.
     */
    _onItemSelected(item, addToInput) {
        if (this.options.multivalued) {
            const $item = $(`<${this.optionTagName}>`)
                .html(this.renderSelectedOption(item));
            const $items = this._$selected.children();
            const text = $item.text();

            if (this.autoAddClose) {
                $('<span class="remove-item ink-i-delete-item">')
                    .click(() => this._onItemRemoved($item, item))
                    .appendTo($item);
            }

            let attached = false;

            for (let i = 0; i < $items.length; i++) {
                const $i = $items.eq(i);

                if ($i.text().localeCompare(text) > 0) {
                    $i.before($item);
                    attached = true;
                    break;
                }
            }

            if (!attached) {
                $item.appendTo(this._$selected);
            }

            this._selectedIDs.set(item.id, item);

            if (addToInput) {
                this._updateInput();
            }
        } else {
            this._selectedIDs = new Map([[item.id, item]]);
            this._updateInput();
        }
    },

    /**
     * Callback for when an item is removed from the list.
     *
     * Args:
     *     $item (jQuery):
     *         The element representing the item in the selected list.
     *
     *     item (object):
     *         The item being removed.
     */
    _onItemRemoved($item, item) {
        $item.remove();
        this._selectedIDs.delete(item.id);
        this._updateInput();
    },

    /**
     * Render an option in the drop-down menu.
     *
     * This should be overridden in order to render type-specific data.
     *
     * Args:
     *     item (object):
     *         The item to render.
     *
     * Returns:
     *     string:
     *     HTML to insert into the drop-down menu.
     */
    renderOption(item) {
        return '';
    },

    /**
     * Render an option in the selected list.
     *
     * By default, this uses the same implementation as renderOption. If a
     * widget wants to display selected options differently, they may override
     * this.
     *
     * Args:
     *     item (object):
     *         The item to render.
     *
     * Returns:
     *     string:
     *     HTML to insert into the selected items list.
     */
    renderSelectedOption(item) {
        return this.renderOption(item);
    },

    /**
     * Load options from the server.
     *
     * This should be overridden in order to make necessary API requests.
     *
     * Args:
     *     query (string):
     *         The string typed in by the user.
     *
     *     callback (function):
     *         A callback to be called once data has been loaded. This should
     *         be passed an array of objects, each representing an option in
     *         the drop-down.
     */
    loadOptions(query, callback) {
        callback();
    },
});
