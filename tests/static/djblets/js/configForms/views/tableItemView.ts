/**
 * View to render a ListItem as a row in a table.
 */

import { spina } from '@beanbag/spina';
import * as _ from 'underscore';

import { type ListItem } from '../models/listItemModel';
import { ListItemView } from './listItemView';


/**
 * View to render a ListItem as a row in a table.
 *
 * This is meant to be used with TableView. Subclasses will generally want
 * to override the template.
 */
@spina
export class TableItemView<
    TModel extends ListItem = ListItem,
    TElement extends HTMLElement = HTMLTableRowElement,
    TExtraViewOptions = unknown,
> extends ListItemView<TModel, TElement, TExtraViewOptions> {
    static tagName = 'tr';

    static template = _.template(dedent`
        <td>
        <% if (editURL) { %>
        <a href="<%- editURL %>"><%- text %></a>
        <% } else { %>
        <%- text %>
        <% } %>
        </td>
    `);

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
    getActionsParent(): JQuery {
        return this.$('td:last');
    }
}
