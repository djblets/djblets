/**
 * A table-based view for a list of items.
 */

import { spina } from '@beanbag/spina';

import { ListView } from './listView';
import { TableItemView } from './tableItemView';


/**
 * A table-based view for a list of items.
 *
 * This is an extension to ListView that's designed for lists with multiple
 * columns of data.
 */
@spina({
    prototypeAttrs: [
        'defaultItemView',
    ],
})
export class TableView extends ListView {
    static tagName = 'table';
    static defaultItemView = TableItemView;

    /**
     * Render the view.
     *
     * If the element does not already have a <tbody>, one will be added.
     * All items will go under this.
     */
    protected onInitialRender() {
        const $body = this.getBody();

        if ($body.length === 0) {
            this.$el.append('<tbody>');
        }

        super.onInitialRender();
    }

    /**
     * Return the body element where items will be added.
     *
     * Returns:
     *     jQuery:
     *     The element where the items will be rendered.
     */
    getBody(): JQuery {
        return this.$('tbody');
    }
}
