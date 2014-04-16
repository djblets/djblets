/*
 * A table-based view for a list of items.
 *
 * This is an extension to ListView that's designed for lists with multiple
 * columns of data.
 */
Djblets.Config.TableView = Djblets.Config.ListView.extend({
    tagName: 'table',

    getBody: function() {
        return this.$('tbody');
    }
});
