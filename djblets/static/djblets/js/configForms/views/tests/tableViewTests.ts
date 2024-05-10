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
    ConfigFormsTableView,
} from 'djblets/configForms';


suite('djblets/configForms/views/TableView', () => {
    describe('Manages rows', () => {
        let collection: Backbone.Collection<ConfigFormsListItem>;
        let list: ConfigFormsList;
        let tableView: ConfigFormsTableView;

        beforeEach(() => {
            collection = new Backbone.Collection<ConfigFormsListItem>(
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

            tableView = new ConfigFormsTableView({
                model: list,
            });
            tableView.render();
        });

        it('On render', () => {
            const $rows = tableView.$('tr');
            expect($rows.length).toBe(3);
            expect($rows.eq(0).text().trim()).toBe('Item 1');
            expect($rows.eq(1).text().trim()).toBe('Item 2');
            expect($rows.eq(2).text().trim()).toBe('Item 3');
        });

        it('On add', () => {
            collection.add({
                text: 'Item 4',
            });

            const $rows = tableView.$('tr');
            expect($rows.length).toBe(4);
            expect($rows.eq(3).text().trim()).toBe('Item 4');
        });

        it('On remove', () => {
            collection.remove(collection.at(0));

            const $rows = tableView.$('tr');
            expect($rows.length).toBe(2);
            expect($rows.eq(0).text().trim()).toBe('Item 2');
        });

        it('On reset', () => {
            collection.reset([
                {text: 'Foo'},
                {text: 'Bar'},
            ]);

            const $rows = tableView.$('tr');
            expect($rows.length).toBe(2);
            expect($rows.eq(0).text().trim()).toBe('Foo');
            expect($rows.eq(1).text().trim()).toBe('Bar');
        });
    });
});
