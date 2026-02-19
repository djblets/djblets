/**
 * Base class for a collection of ListItems.
 */

import { BaseCollection, spina } from '@beanbag/spina';


/**
 * Base class for a collection of ListItems.
 *
 * This operates just like a standard :js:class:`Backbone.Collection`, with two
 * additions:
 *
 * 1. It stores the provided options, for later usage, preventing subclasses
 *    from having to provide their own initialize function.
 *
 * 2. It emits a "fetching" event when calling :js:meth:`fetch`, allowing views
 *    to provide a visual indication when items are being fetched or rendered.
 */
@spina
export class ListItems<
    TModel extends Backbone.Model = Backbone.Model,
    TExtraCollectionOptions = unknown,
    TCollectionOptions extends Backbone.CollectionOptions<TModel> =
        Backbone.CollectionOptions<TModel>
> extends BaseCollection<TModel, TExtraCollectionOptions, TCollectionOptions> {
    /**********************
     * Instance variables *
     **********************/

    /** The saved options. */
    options: TExtraCollectionOptions;

    /**
     * Initialize the collection.
     *
     * Args:
     *     models (array):
     *         The models to add to the collection.
     *
     *     options (object):
     *         Options for the collection.
     */
    initialize(
        models?: TModel[],
        options?: Backbone.CombinedCollectionConstructorOptions<
            TExtraCollectionOptions,
            TModel
        >,
    ) {
        this.options = options;
    }

    /**
     * Fetch the contents of the collection.
     *
     * This will emit the ``fetching`` event, and then call
     * Backbone.Collection's fetch().
     *
     * Args:
     *     options (object):
     *         Options to pass to the base class's ``fetch`` method.
     */
    fetch(
        options: Backbone.CollectionFetchOptions,
    ): JQueryXHR {
        this.trigger('fetching');

        return super.fetch(options);
    }
}
