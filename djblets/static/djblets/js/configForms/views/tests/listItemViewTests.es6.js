suite('djblets/configForms/views/ListItemView', () => {
    describe('Rendering', () => {
        describe('Item display', () => {
            it('With editURL', () => {
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

            it('Without editURL', () => {
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

        describe('Actions', () => {
            it('Checkboxes', () => {
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

            describe('Buttons', () => {
                it('Simple', () => {
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

                it('Danger', () => {
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

                it('Icon names', () => {
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

            describe('Menus', () => {
                let item;
                let itemView;

                beforeEach(() => {
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

                it('Initial display', () => {
                    const $button = itemView.$(
                        'button.djblets-c-config-forms-list__item-action');

                    expect($button.length).toBe(1);
                    expect($button.text()).toBe('Menu ▾');
                });

                it('Opening', () => {

                    /* Prevent deferring. */
                    spyOn(_, 'defer').and.callFake(function(cb) {
                        cb();
                    });

                    spyOn(itemView, 'trigger');

                    const $action = itemView
                        .$('.config-forms-list-action-mymenu');
                    $action.click();

                    const $menu = itemView.$('.action-menu');
                    expect($menu.length).toBe(1);
                    expect(itemView.trigger.calls.mostRecent().args[0]).toBe(
                        'actionMenuPopUp');
                });

                it('Closing', () => {
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

        describe('Action properties', () => {
            describe('enabledPropName', () => {
                it('value == undefined', () => {
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

                it('value == true', () => {
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

                it('value == false', () => {
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

                describe('with enabledPropInverse == true', () => {
                    it('value == undefined', () => {
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

                    it('value == true', () => {
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

                    it('value == false', () => {
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

    describe('Action handlers', () => {
        it('Buttons', () => {
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

        it('Checkboxes', () => {
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
