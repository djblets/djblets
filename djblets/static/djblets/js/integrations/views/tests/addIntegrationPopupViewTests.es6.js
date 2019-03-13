suite('djblets/integrations/views/AddIntegrationPopupView', function() {
    describe('Rendering', function() {
        it('With integrations', function() {
            const view = new Djblets.AddIntegrationPopupView({
                integrations: [
                    {
                        'addURL': 'int1/add/',
                        'description': 'Int1 Description',
                        'iconSrc': 'data:test,int1',
                        'iconSrcSet': 'data:test,int1 1x, data:test,int1@2x 2x',
                        'id': 'int1',
                        'name': 'Int1',
                    },
                    {
                        'addURL': 'int2/add/',
                        'description': 'Int2 Description',
                        'iconSrc': 'data:test,int2',
                        'iconSrcSet': 'data:test,int2 1x, data:test,int2@2x 2x',
                        'id': 'int2',
                        'name': 'Int2',
                    },
                ],
            });
            view.render();

            expect(view.$el.hasClass('-is-empty')).toBe(false);

            const $items = view.$el.find('.djblets-c-integration');
            expect($items.length).toBe(2);

            /* Check the first integration. */
            let $item = $items.eq(0);
            expect($item.children('a').attr('href')).toBe('int1/add/');
            expect($item.find('.djblets-c-integration__name').text())
                .toBe('Int1');
            expect($item.find('.djblets-c-integration__description')
                       .text().trim())
                .toBe('Int1 Description');

            let $icon = $item.find('.djblets-c-integration__icon');
            expect($icon.attr('src')).toBe('data:test,int1');
            expect($icon.attr('srcset'))
                .toBe('data:test,int1 1x, data:test,int1@2x 2x');

            /* Check the second integration. */
            $item = $items.eq(1);
            expect($item.children('a').attr('href')).toBe('int2/add/');
            expect($item.find('.djblets-c-integration__name').text())
                .toBe('Int2');
            expect($item.find('.djblets-c-integration__description')
                       .text().trim())
                .toBe('Int2 Description');

            $icon = $item.find('.djblets-c-integration__icon');
            expect($icon.attr('src')).toBe('data:test,int2');
            expect($icon.attr('srcset'))
                .toBe('data:test,int2 1x, data:test,int2@2x 2x');
        });

        it('Without integrations', function() {
            const view = new Djblets.AddIntegrationPopupView({
                integrations: [],
            });
            view.render();

            expect(view.$el.hasClass('-is-empty')).toBe(true);

            const $empty = view.$('.djblets-c-integrations-popup__empty');
            expect($empty.length).toBe(1);

            expect($empty.text().trim()).toBe(
                'There are no integrations currently installed.');
        });
    });
});
