suite('djblets/configForms/views/TableItemView', function() {
    describe('Rendering', function() {
        describe('Item display', function() {
            it('With editURL', function() {
                const item = new Djblets.Config.ListItem({
                    editURL: 'http://example.com/',
                    text: 'Label',
                });
                const itemView = new Djblets.Config.TableItemView({
                    model: item,
                });

                itemView.render();
                expect(itemView.$el.html().strip()).toBe([
                    '<td>',
                    '<span class="djblets-c-config-forms-list__item-actions">',
                    '</span>\n\n',
                    '<a href="http://example.com/">Label</a>\n\n',
                    '</td>',
                ].join(''));
            });

            it('Without editURL', function() {
                const item = new Djblets.Config.ListItem({
                    text: 'Label',
                });
                const itemView = new Djblets.Config.TableItemView({
                    model: item,
                });

                itemView.render();
                expect(itemView.$el.html().strip()).toBe([
                    '<td>',
                    '<span class="djblets-c-config-forms-list__item-actions">',
                    '</span>\n\n',
                    'Label\n\n',
                    '</td>',
                ].join(''));
            });
        });

        describe('Action placement', function() {
            it('Default template', function() {
                const item = new Djblets.Config.ListItem({
                    text: 'Label',
                    actions: [
                        {
                            id: 'mybutton',
                            label: 'Button',
                        },
                    ],
                });
                const itemView = new Djblets.Config.TableItemView({
                    model: item,
                });

                itemView.render();

                const $button = itemView.$(
                    'td:last button.djblets-c-config-forms-list__item-action');
                expect($button.length).toBe(1);
                expect($button.text()).toBe('Button');
            });

            it('Custom template', function() {
                const CustomTableItemView =
                    Djblets.Config.TableItemView.extend({
                        template: _.template(dedent`
                            <td></td>
                            <td></td>
                        `),
                    });
                const item = new Djblets.Config.ListItem({
                    text: 'Label',
                    actions: [
                        {
                            id: 'mybutton',
                            label: 'Button',
                        },
                    ],
                });
                const itemView = new CustomTableItemView({
                    model: item,
                });

                itemView.render();

                const $button = itemView.$(
                    'td:last button.djblets-c-config-forms-list__item-action');
                expect($button.length).toBe(1);
                expect($button.text()).toBe('Button');
            });
        });
    });
});
