import {
    beforeEach,
    describe,
    expect,
    it,
    suite,
} from 'jasmine-core';

import { List } from '../../models/listModel';
import { ListItem } from '../../models/listItemModel';
import { ListView } from '../listView';


suite('djblets/configForms/views/ListView', () => {
    describe('Manages items', () => {
        let collection;
        let list;
        let listView;

        beforeEach(() => {
            collection = new Backbone.Collection(
                [
                    {text: 'Item 1'},
                    {text: 'Item 2'},
                    {text: 'Item 3'},
                ], {
                    model: ListItem,
                }
            );

            list = new List({}, {
                collection: collection,
            });

            listView = new ListView({
                model: list,
            });
            listView.render();
        });

        it('On render', () => {
            const $items = listView.$('li');
            expect($items.length).toBe(3);
            expect($items.eq(0).text().strip()).toBe('Item 1');
            expect($items.eq(1).text().strip()).toBe('Item 2');
            expect($items.eq(2).text().strip()).toBe('Item 3');
        });

        it('On add', () => {
            collection.add({
                text: 'Item 4',
            });

            const $items = listView.$('li');
            expect($items.length).toBe(4);
            expect($items.eq(3).text().strip()).toBe('Item 4');
        });

        it('On remove', () => {
            collection.remove(collection.at(0));

            const $items = listView.$('li');
            expect($items.length).toBe(2);
            expect($items.eq(0).text().strip()).toBe('Item 2');
        });

        it('On reset', () => {
            collection.reset([
                {text: 'Foo'},
                {text: 'Bar'},
            ]);

            const $items = listView.$('li');
            expect($items.length).toBe(2);
            expect($items.eq(0).text().strip()).toBe('Foo');
            expect($items.eq(1).text().strip()).toBe('Bar');
        });
    });
});
