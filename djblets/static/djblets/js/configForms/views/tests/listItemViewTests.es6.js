suite('djblets/configForms/views/ListItemView', function() {
    describe('Rendering', function() {
        describe('General item display', function() {
            it('With editURL', function() {
                const item = new Djblets.Config.ListItem({
                    editURL: 'http://example.com/',
                    text: 'Label',
                });
                const itemView = new Djblets.Config.ListItemView({
                    model: item,
                });

                itemView.render();
                expect(itemView.$el.html().strip()).toBe([
                    '<span class="djblets-c-config-forms-list__item-actions">',
                    '</span>\n',
                    '<a href="http://example.com/">Label</a>',
                ].join(''));
            });

            it('Without editURL', function() {
                const item = new Djblets.Config.ListItem({
                    text: 'Label',
                });
                const itemView = new Djblets.Config.ListItemView({
                    model: item,
                });

                itemView.render();
                expect(itemView.$el.html().strip()).toBe([
                    '<span class="djblets-c-config-forms-list__item-actions">',
                    '</span>\n',
                    'Label',
                ].join(''));
            });
        });

        describe('Item states', function() {
            const CustomItemView = Djblets.Config.ListItemView.extend({
                template: _.template(dedent`
                    <div><%- text %></div>
                    <div class="djblets-c-config-forms-list__item-state">
                    </div>
                `),
            });

            it('Initial render', function() {
                const item = new Djblets.Config.ListItem({
                    itemState: 'enabled',
                });
                const itemView = new CustomItemView({
                    model: item,
                });

                itemView.render();

                expect(itemView.el).toHaveClass('-is-enabled');

                const $stateText =
                    itemView.$('.djblets-c-config-forms-list__item-state');
                expect($stateText.text()).toBe('Enabled');
            });

            it('When changed', function() {
                const item = new Djblets.Config.ListItem({
                    itemState: 'enabled',
                });
                const itemView = new CustomItemView({
                    model: item,
                });

                itemView.render();

                item.set('itemState', 'disabled');

                expect(itemView.el).toHaveClass('-is-disabled');
                expect(itemView.el).not.toHaveClass('-is-enabled');

                const $stateText =
                    itemView.$('.djblets-c-config-forms-list__item-state');
                expect($stateText.text()).toBe('Disabled');
            });
        });

        describe('Actions', function() {
            it('Checkboxes', function() {
                const item = new Djblets.Config.ListItem({
                    text: 'Label',
                    checkboxAttr: false,
                    actions: [
                        {
                            id: 'mycheckbox',
                            type: 'checkbox',
                            label: 'Checkbox',
                            propName: 'checkboxAttr',
                        },
                    ],
                });
                const itemView = new Djblets.Config.ListItemView({
                    model: item,
                });

                itemView.render();

                expect(itemView.$('input[type=checkbox]').length).toBe(1);
                expect(itemView.$('label').length).toBe(1);
            });

            describe('Buttons', function() {
                it('Simple', function() {
                    const item = new Djblets.Config.ListItem({
                        text: 'Label',
                        actions: [
                            {
                                id: 'mybutton',
                                label: 'Button',
                            },
                        ],
                    });
                    const itemView = new Djblets.Config.ListItemView({
                        model: item,
                    });

                    itemView.render();

                    const $button = itemView.$(
                        'button.djblets-c-config-forms-list__item-action');
                    expect($button.length).toBe(1);
                    const buttonEl = $button[0];

                    expect($button.text()).toBe('Button');
                    expect(buttonEl)
                        .toHaveClass('config-forms-list-action-mybutton');
                    expect(buttonEl).not.toHaveClass('rb-icon');
                    expect(buttonEl).not.toHaveClass('-is-danger');
                    expect(buttonEl).not.toHaveClass('-is-primary');
                });

                it('Danger', function() {
                    const item = new Djblets.Config.ListItem({
                        text: 'Label',
                        actions: [
                            {
                                id: 'mybutton',
                                label: 'Button',
                                danger: true,
                            },
                        ],
                    });
                    const itemView = new Djblets.Config.ListItemView({
                        model: item,
                    });

                    itemView.render();

                    const $button = itemView.$(
                        'button.djblets-c-config-forms-list__item-action');
                    expect($button.length).toBe(1);
                    const buttonEl = $button[0];

                    expect($button.text()).toBe('Button');
                    expect(buttonEl)
                        .toHaveClass('config-forms-list-action-mybutton');
                    expect(buttonEl).not.toHaveClass('rb-icon');
                    expect(buttonEl).not.toHaveClass('-is-primary');
                    expect(buttonEl).toHaveClass('-is-danger');
                });

                it('Primary', function() {
                    const item = new Djblets.Config.ListItem({
                        text: 'Label',
                        actions: [
                            {
                                id: 'mybutton',
                                label: 'Button',
                                primary: true,
                            },
                        ],
                    });
                    const itemView = new Djblets.Config.ListItemView({
                        model: item,
                    });

                    itemView.render();

                    const $button = itemView.$(
                        'button.djblets-c-config-forms-list__item-action');
                    expect($button.length).toBe(1);
                    const buttonEl = $button[0];

                    expect($button.text()).toBe('Button');
                    expect(buttonEl)
                        .toHaveClass('config-forms-list-action-mybutton');
                    expect(buttonEl).not.toHaveClass('rb-icon');
                    expect(buttonEl).not.toHaveClass('-is-danger');
                    expect(buttonEl).toHaveClass('-is-primary');
                });

                it('Icon names', function() {
                    const item = new Djblets.Config.ListItem({
                        text: 'Label',
                        actions: [
                            {
                                id: 'mybutton',
                                label: 'Button',
                                danger: false,
                                iconName: 'foo',
                            },
                        ],
                    });
                    const itemView = new Djblets.Config.ListItemView({
                        model: item,
                    });

                    itemView.render();

                    const $button = itemView.$(
                        'button.djblets-c-config-forms-list__item-action');
                    expect($button.length).toBe(1);
                    const buttonEl = $button[0];

                    expect($button.text()).toBe('Button');
                    expect(buttonEl)
                        .toHaveClass('config-forms-list-action-mybutton');
                    expect(buttonEl).not.toHaveClass('-is-danger');
                    expect(buttonEl).not.toHaveClass('-is-primary');

                    const $span = $button.find('span');
                    expect($span.length).toBe(1);
                    expect($span.hasClass('djblets-icon')).toBe(true);
                    expect($span.hasClass('djblets-icon-foo')).toBe(true);
                });
            });

            describe('Menus', function() {
                let item;
                let itemView;

                beforeEach(function() {
                    item = new Djblets.Config.ListItem({
                        text: 'Label',
                        actions: [
                            {
                                id: 'mymenu',
                                label: 'Menu',
                                children: [
                                    {
                                        id: 'mymenuitem',
                                        label: 'My menu item',
                                    },
                                ],
                            },
                        ],
                    });

                    itemView = new Djblets.Config.ListItemView({
                        model: item,
                    });

                    itemView.render();
                });

                it('Initial display', function() {
                    const $button = itemView.$(
                        'button.djblets-c-config-forms-list__item-action');

                    expect($button.length).toBe(1);
                    expect($button.text()).toBe('Menu ▾');
                });

                it('Opening', function() {
                    /* Prevent deferring. */
                    spyOn(_, 'defer').and.callFake(function(cb) {
                        cb();
                    });

                    spyOn(itemView, 'trigger');

                    const $action = itemView
                        .$('.config-forms-list-action-mymenu');
                    $action.click();

                    const $menu =
                        itemView.$('.djblets-c-config-forms-popup-menu');
                    expect($menu.length).toBe(1);
                    expect(itemView.trigger.calls.mostRecent().args[0]).toBe(
                        'actionMenuPopUp');
                });

                it('Closing', function() {
                    /* Prevent deferring. */
                    spyOn(_, 'defer').and.callFake(cb => cb());

                    const $action = itemView
                        .$('.config-forms-list-action-mymenu');
                    $action.click();

                    spyOn(itemView, 'trigger');
                    $(document.body).click();

                    expect(itemView.trigger.calls.mostRecent().args[0]).toBe(
                        'actionMenuPopDown');

                    const $menu = itemView.$('.action-menu');
                    expect($menu.length).toBe(0);
                });
            });
        });

        describe('Action properties', function() {
            describe('enabledPropName', function() {
                it('value == undefined', function() {
                    const item = new Djblets.Config.ListItem({
                        text: 'Label',
                        actions: [
                            {
                                id: 'mycheckbox',
                                type: 'checkbox',
                                label: 'Checkbox',
                                enabledPropName: 'isEnabled',
                            },
                        ],
                    });
                    const itemView = new Djblets.Config.ListItemView({
                        model: item,
                    });

                    itemView.render();

                    const $action = itemView
                        .$('.config-forms-list-action-mycheckbox');

                    expect($action.prop('disabled')).toBe(true);
                });

                it('value == true', function() {
                    const item = new Djblets.Config.ListItem({
                        text: 'Label',
                        isEnabled: true,
                        actions: [
                            {
                                id: 'mycheckbox',
                                type: 'checkbox',
                                label: 'Checkbox',
                                enabledPropName: 'isEnabled',
                            },
                        ],
                    });
                    const itemView = new Djblets.Config.ListItemView({
                        model: item,
                    });

                    itemView.render();

                    const $action = itemView
                        .$('.config-forms-list-action-mycheckbox');

                    expect($action.prop('disabled')).toBe(false);
                });

                it('value == false', function() {
                    const item = new Djblets.Config.ListItem({
                        text: 'Label',
                        isEnabled: false,
                        actions: [
                            {
                                id: 'mycheckbox',
                                type: 'checkbox',
                                label: 'Checkbox',
                                enabledPropName: 'isEnabled',
                            },
                        ],
                    });
                    const itemView = new Djblets.Config.ListItemView({
                        model: item
                    });

                    itemView.render();

                    const $action = itemView
                        .$('.config-forms-list-action-mycheckbox');

                    expect($action.prop('disabled')).toBe(true);
                });

                describe('with enabledPropInverse == true', function() {
                    it('value == undefined', function() {
                        const item = new Djblets.Config.ListItem({
                            text: 'Label',
                            actions: [
                                {
                                    id: 'mycheckbox',
                                    type: 'checkbox',
                                    label: 'Checkbox',
                                    enabledPropName: 'isDisabled',
                                    enabledPropInverse: true,
                                },
                            ],
                        });
                        const itemView = new Djblets.Config.ListItemView({
                            model: item
                        });

                        itemView.render();

                        const $action = itemView
                            .$('.config-forms-list-action-mycheckbox');

                        expect($action.prop('disabled')).toBe(false);
                    });

                    it('value == true', function() {
                        const item = new Djblets.Config.ListItem({
                            text: 'Label',
                            isDisabled: true,
                            actions: [
                                {
                                    id: 'mycheckbox',
                                    type: 'checkbox',
                                    label: 'Checkbox',
                                    enabledPropName: 'isDisabled',
                                    enabledPropInverse: true,
                                },
                            ],
                        });
                        const itemView = new Djblets.Config.ListItemView({
                            model: item,
                        });

                        itemView.render();

                        const $action = itemView
                            .$('.config-forms-list-action-mycheckbox');

                        expect($action.prop('disabled')).toBe(true);
                    });

                    it('value == false', function() {
                        var item = new Djblets.Config.ListItem({
                                text: 'Label',
                                isDisabled: false,
                                actions: [
                                    {
                                        id: 'mycheckbox',
                                        type: 'checkbox',
                                        label: 'Checkbox',
                                        enabledPropName: 'isDisabled',
                                        enabledPropInverse: true
                                    }
                                ]
                            }),
                            itemView = new Djblets.Config.ListItemView({
                                model: item
                            }),
                            $action;

                        itemView.render();

                        $action =
                            itemView.$('.config-forms-list-action-mycheckbox');

                        expect($action.prop('disabled')).toBe(false);
                    });
                });
            });
        });
    });

    describe('Action handlers', function() {
        it('Buttons', function() {
            var item = new Djblets.Config.ListItem({
                text: 'Label',
                actions: [
                    {
                        id: 'mybutton',
                        label: 'Button',
                    },
                ],
            });
            const itemView = new Djblets.Config.ListItemView({
                model: item
            });

            itemView.actionHandlers = {
                mybutton: '_onMyButtonClick'
            };
            itemView._onMyButtonClick = () => {};
            spyOn(itemView, '_onMyButtonClick');

            itemView.render();

            const $button = itemView.$(
                'button.djblets-c-config-forms-list__item-action');
            expect($button.length).toBe(1);
            $button.click();

            expect(itemView._onMyButtonClick).toHaveBeenCalled();
        });

        it('Checkboxes', function() {
            const item = new Djblets.Config.ListItem({
                text: 'Label',
                checkboxAttr: false,
                actions: [
                    {
                        id: 'mycheckbox',
                        type: 'checkbox',
                        label: 'Checkbox',
                        propName: 'checkboxAttr',
                    },
                ],
            });
            const itemView = new Djblets.Config.ListItemView({
                model: item,
            });

            itemView.actionHandlers = {
                mybutton: '_onMyButtonClick',
            };
            itemView._onMyButtonClick = () => {};
            spyOn(itemView, '_onMyButtonClick');

            itemView.render();

            const $checkbox = itemView.$('input[type=checkbox]');
            expect($checkbox.length).toBe(1);
            expect($checkbox.prop('checked')).toBe(false);
            $checkbox
                .prop('checked', true)
                .triggerHandler('change');

            expect(item.get('checkboxAttr')).toBe(true);
        });
    });
});
