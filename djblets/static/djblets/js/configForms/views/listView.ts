/**
 * View for displaying a list of items.
 */

import { BaseView, Class, spina } from '@beanbag/spina';
import type * as Backbone from 'backbone';
import * as _ from 'underscore';

import { type List } from '../models/listModel';
import { ListItemView } from './listItemView';


/**
 * Options for the ListView.
 *
 * Version Added:
 *     4.0
 */
export interface ListViewOptions {
    /** The item view class. */
    ItemView?: Class<ListItemView>;

    /** Whether to animate added or removed items with a fade. */
    animateItems?: boolean;
}


/** Options for add and remove methods. */
interface AddRemoveOptions {
    /** Whether to animate the change. */
    animate?: boolean;
}


/**
 * View for displaying a list of items.
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
@spina({
    prototypeAttrs: [
        'defaultItemView',
    ],
})
export class ListView<
    TModel extends List = List,
    TElement extends HTMLUListElement = HTMLUListElement,
    TExtraViewOptions extends ListViewOptions = ListViewOptions
> extends BaseView<TModel, TElement, TExtraViewOptions> {
    static className = 'djblets-c-config-forms-list';
    static tagName = 'ul';

    static defaultItemView: Class<ListItemView> = ListItemView;
    defaultItemView: Class<ListItemView>;

    /**********************
     * Instance variables *
     **********************/

    /** The item view class. */
    ItemView: typeof Backbone.View;

    /** Whether to animate addition or removal of items. */
    animateItems: boolean;

    /** The set of views for all list items. */
    views: Backbone.View[];

    /**
     * The main list element.
     *
     * This is set on render based on the result of :js:meth:`getBody`.
     */
    $listBody: JQuery = null;

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
    initialize(options: Partial<ListViewOptions> = {}) {
        const collection = this.model.collection;

        this.ItemView = options.ItemView || this.defaultItemView;
        this.views = [];
        this.animateItems = !!options.animateItems;

        this.once('rendered', () => {
            this.listenTo(collection, 'add', this.addItem);
            this.listenTo(collection, 'remove', this.removeItem);
            this.listenTo(collection, 'reset', this.#renderItems);
        });
    }

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
    getBody(): JQuery {
        return this.$el;
    }

    /**
     * Render the list of items.
     *
     * This will loop through all items and render each one.
     */
    protected onRender() {
        this.$listBody = this.getBody();

        this.#renderItems();
        this.trigger('rendered');
    }

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
     *     options (AddRemoveOptions, optional):
     *         Options for adding the item.
     */
    protected addItem(
        item: Backbone.Model,
        collection: Backbone.Collection,
        options: AddRemoveOptions = {},
    ) {
        const animateItem = (options.animate !== false);
        const view = new this.ItemView({
            model: item,
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
    }

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
    protected removeItem(
        item: Backbone.Model,
        collection: Backbone.Collection,
        options: AddRemoveOptions = {},
    ) {
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
    }

    /**
     * Render all items from the list.
     */
    #renderItems() {
        this.views.forEach(view => view.remove());
        this.views = [];
        this.$listBody.empty();

        this.model.collection.each(item => {
            this.addItem(item, item.collection, {
                animate: false,
            });
        });
    }
}
