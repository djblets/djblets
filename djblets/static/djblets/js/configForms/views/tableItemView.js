/*
 * Renders a ListItem as a row in a table.
 *
 * This is meant to be used with TableView. Subclasses will generally want
 * to override the template.
 */
Djblets.Config.TableItemView = Djblets.Config.ListItemView.extend({
    tagName: 'tr',

    template: _.template([
        '<td>',
        ' <% if (editURL) { %>',
        '  <a href="<%- editURL %>"><%- text %></a>',
        ' <% } else { %>',
        '  <%- text %>',
        ' <% } %>',
        '</td>'
    ].join(''))
});
