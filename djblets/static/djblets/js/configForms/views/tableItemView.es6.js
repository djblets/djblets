/**
 * Renders a ListItem as a row in a table.
 *
 * This is meant to be used with TableView. Subclasses will generally want
 * to override the template.
 */
Djblets.Config.TableItemView = Djblets.Config.ListItemView.extend({
    tagName: 'tr',

    template: _.template(dedent`
        <td>
        <% if (editURL) { %>
        <a href="<%- editURL %>"><%- text %></a>
        <% } else { %>
        <%- text %>
        <% } %>
        </td>
    `),

    /**
     * Return the container for the actions.
     *
     * This defaults to being the last cell in the row, but this can be
     * overridden to provide a specific cell or an element within.
     *
     * Returns:
     *     jQuery:
     *     The element where actions should be rendered.
     */
    getActionsParent() {
        return this.$('td:last');
    },
});
