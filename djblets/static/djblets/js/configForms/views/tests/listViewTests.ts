import {
    beforeEach,
    describe,
    expect,
    it,
    suite,
} from 'jasmine-core';
import * as Backbone from 'backbone';

import {
    ConfigFormsList,
    ConfigFormsListItem,
    ConfigFormsListView,
} from 'djblets/configForms';


suite('djblets/configForms/views/ListView', () => {
    let collection: Backbone.Collection;
    let list: ConfigFormsList;
    let listView: ConfigFormsListView;

    beforeEach(() => {
        collection = new Backbone.Collection(
            [
                {text: 'Item 1'},
                {text: 'Item 2'},
                {text: 'Item 3'},
            ], {
                model: ConfigFormsListItem,
            }
        );

        list = new ConfigFormsList({}, {
            collection: collection,
        });

        listView = new ConfigFormsListView({
            model: list,
        });
    });

    describe('Methods', () => {
        describe('render', () => {
            it('On first render', () => {
                expect(listView.$listBody).toBeNull();
                expect(listView.$('li').length).toBe(0);

                listView.render();

                expect(listView.$listBody).toBe(listView.$el);
                expect(listView.$('li').length).toBe(3);
            });

            it('On subsequent render', () => {
                expect(listView.$listBody).toBeNull();
                expect(listView.$('li').length).toBe(0);

                /* First render. */
                listView.render();

                expect(listView.$listBody).toBe(listView.$el);
                expect(listView.$('li').length).toBe(3);

                /* Modify some state. */
                listView.$el.append('<button>');
                listView.$listBody = $('<input>');

                /* Second render. */
                listView.render();

                expect(listView.$listBody).toBe(listView.$el);
                expect(listView.$('li').length).toBe(3);
                expect(listView.$('button').length).toBe(0);
                expect(listView.$('input').length).toBe(0);
            });
        });
    });

    describe('Manages items', () => {
        beforeEach(() => {
            listView.render();
        });

        it('On render', () => {
            const $items = listView.$('li');
            expect($items.length).toBe(3);
            expect($items.eq(0).text().trim()).toBe('Item 1');
            expect($items.eq(1).text().trim()).toBe('Item 2');
            expect($items.eq(2).text().trim()).toBe('Item 3');
        });

        it('On add', () => {
            collection.add({
                text: 'Item 4',
            });

            const $items = listView.$('li');
            expect($items.length).toBe(4);
            expect($items.eq(3).text().trim()).toBe('Item 4');
        });

        it('On remove', () => {
            collection.remove(collection.at(0));

            const $items = listView.$('li');
            expect($items.length).toBe(2);
            expect($items.eq(0).text().trim()).toBe('Item 2');
        });

        it('On reset', () => {
            collection.reset([
                {text: 'Foo'},
                {text: 'Bar'},
            ]);

            const $items = listView.$('li');
            expect($items.length).toBe(2);
            expect($items.eq(0).text().trim()).toBe('Foo');
            expect($items.eq(1).text().trim()).toBe('Bar');
        });
    });
});
