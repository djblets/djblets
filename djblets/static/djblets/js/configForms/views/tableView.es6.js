/**
 * A table-based view for a list of items.
 *
 * This is an extension to ListView that's designed for lists with multiple
 * columns of data.
 */
Djblets.Config.TableView = Djblets.Config.ListView.extend({
    tagName: 'table',
    defaultItemView: Djblets.Config.TableItemView,

    /**
     * Render the view.
     *
     * If the element does not already have a <tbody>, one will be added.
     * All items will go under this.
     *
     * Returns:
     *     Djblets.Config.TableView:
     *     This view.
     */
    render() {
        const $body = this.getBody();

        if ($body.length === 0) {
            this.$el.append('<tbody>');
        }

        return Djblets.Config.ListView.prototype.render.call(this);
    },

    /**
     * Return the body element where items will be added.
     *
     * Returns:
     *     jQuery:
     *     The element where the items will be rendered.
     */
    getBody() {
        return this.$('tbody');
    },
});
