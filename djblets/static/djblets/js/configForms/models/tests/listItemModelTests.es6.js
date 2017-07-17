suite('djblets/configForms/models/ListItem', () => {
    describe('Default actions', () => {
        describe('showRemove', () =>  {
            it('true', () => {
                const listItem = new Djblets.Config.ListItem({
                    showRemove: true,
                });

                expect(listItem.actions.length).toBe(1);
                expect(listItem.actions[0].id).toBe('delete');
            });

            it('false', () => {
                const listItem = new Djblets.Config.ListItem({
                    showRemove: false,
                });

                expect(listItem.actions.length).toBe(0);
            });
        });
    });
});
