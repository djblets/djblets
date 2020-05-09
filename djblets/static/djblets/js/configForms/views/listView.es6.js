/**
 * Display a list of items.
 *
 * This will render each item in a list, and update that list when the
 * items in the collection changes.
 *
 * It can also filter the displayed list of items.
 *
 * If loading the list through the API, this will display a loading indicator
 * until the items have been loaded.
 *
 * If 'options.animateItems' is true, then newly added or removed items will
 * be faded in/out.
 */
Djblets.Config.ListView = Backbone.View.extend({
    tagName: 'ul',
    className: 'djblets-c-config-forms-list',
    defaultItemView: Djblets.Config.ListItemView,

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object, optional):
     *         The view options.
     *
     * Option Args:
     *     ItemView (object):
     *         The item view class to use. This argument defaults to
     *         :js:attr:`defaultItemView`.
     *
     *     animateItems (boolean):
     *         Whether or not items should be animated. This argument
     *         defaults to ``false``.
     */
    initialize(options={}) {
        const collection = this.model.collection;

        this.ItemView = options.ItemView || this.defaultItemView;
        this.views = [];
        this.animateItems = !!options.animateItems;

        this.once('rendered', () => {
            this.listenTo(collection, 'add', this._addItem);
            this.listenTo(collection, 'remove', this._removeItem);
            this.listenTo(collection, 'reset', this._renderItems);
        });
    },

    /**
     * Return the body element.
     *
     * This can be overridden by subclasses if the list items should be
     * rendered to a child element of this view.
     *
     * Returns:
     *     jQuery:
     *     Where the list view should be rendered.
     */
    getBody() {
        return this.$el;
    },

    /**
     * Render the list of items.
     *
     * This will loop through all items and render each one.
     *
     * Returns:
     *     Djblets.Config.ListView:
     *     This view.
     */
    render() {
        this.$listBody = this.getBody();

        this._renderItems();
        this.trigger('rendered');

        return this;
    },

    /**
     * Create a view for an item and adds it.
     *
     * Args:
     *     item (Backbone.Model):
     *         The model to add.
     *
     *     collection (Backbone.Collection):
     *         Ignored.
     *
     *     options (object, optional):
     *         Options for adding the item.
     *
     * Option Args:
     *     animate (boolean):
     *         Whether or not to animate adding the item. This argument defaults
     *         to ``true``.
     */
    _addItem(item, collection, options={}) {
        const animateItem = (options.animate !== false);
        const view = new this.ItemView({
            model: item
        });

        view.render();

        /*
         * If this ListView has animation enabled, and this specific
         * item is being animated (the default unless options.animate
         * is false), we'll fade in the item.
         */
        if (this.animateItems && animateItem) {
            view.$el.fadeIn();
        }

        this.$listBody.append(view.$el);
        this.views.push(view);
    },

    /**
     * Handle an item being removed from the collection.
     *
     * Removes the element from the list.
     *
     * Args:
     *     item (Backbone.Model):
     *         The model to remove.
     *
     *     collection (Backbone.Collection):
     *         Ignored.
     *
     *     options (object, optional):
     *         Options for removing the element.
     *
     * Option Args:
     *     animate (boolean):
     *         Whether or not the removal should be animated. This defaults
     *         to ``true``.
     */
    _removeItem(item, collection, options={}) {
        const animateItem = (options.animate !== false);
        const view = _.find(this.views, view => view.model === item);

        if (view) {
            this.views = _.without(this.views, view);

            /*
             * If this ListView has animation enabled, and this specific
             * item is being animated (the default unless options.animate
             * is false), we'll fade out the item.
             */
            if (this.animateItems && animateItem) {
                view.$el.fadeOut(function() {
                    view.remove();
                });
            } else {
                view.remove();
            }
        }
    },

    /**
     * Render all items from the list.
     */
    _renderItems() {
        this.views.forEach(function(view) {
            view.remove();
        });
        this.views = [];
        this.$listBody.empty();

        this.model.collection.each(item => {
            this._addItem(item, item.collection, {
                animate: false
            });
        });
    },
});
