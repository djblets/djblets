import {
    describe,
    expect,
    it,
} from 'jasmine-core';

import { ConfigFormsListItem } from 'djblets/configForms';


suite('djblets/configForms/models/ListItem', () => {
    describe('Default actions', () => {
        describe('showRemove', () => {
            it('true', () => {
                const listItem = new ConfigFormsListItem({
                    showRemove: true,
                });

                expect(listItem.actions.length).toBe(1);
                expect(listItem.actions[0].id).toBe('delete');
            });

            it('false', () => {
                const listItem = new ConfigFormsListItem({
                    showRemove: false,
                });

                expect(listItem.actions.length).toBe(0);
            });
        });
    });
});
