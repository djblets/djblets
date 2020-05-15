suite('djblets/integrations/views/IntegrationConfigListView', function() {
    const template = _.template(dedent`
        <div class="djblets-c-integration-configs">
         <div class="djblets-l-config-forms-container">
          <table class="djblets-c-config-forms-list"></table>
         </div>
        </div>
    `);
    let collection;
    let view;

    beforeEach(function() {
        const $el = $(template()).appendTo($testsScratch);

        view = new Djblets.IntegrationConfigListView({
            el: $el,
            configs: [
                {
                    'editURL' : 'configs/1/',
                    'enabled': true,
                    'id': 1,
                    'integrationID': 'int1',
                    'name': 'Config 1',
                },
                {
                    'editURL' : 'configs/2/',
                    'enabled': true,
                    'id': 2,
                    'integrationID': 'int2',
                    'name': 'Config 2',
                },
                {
                    'editURL' : 'configs/3/',
                    'enabled': false,
                    'id': 3,
                    'integrationID': 'int3',
                    'name': 'Config 3',
                },
                {
                    'editURL' : 'configs/4/',
                    'enabled': true,
                    'id': 4,
                    'integrationID': 'int1',
                    'name': 'Config 4',
                },
            ],
            integrationIDs: ['int1', 'int2', 'int3'],
            integrationsMap: {
                int1: {
                    'addURL': 'int1/add/',
                    'description': 'Int1 Description',
                    'iconSrc': 'data:test,int1',
                    'iconSrcSet': 'data:test,int1 1x, data:test,int1@2x 2x',
                    'id': 'int1',
                    'name': 'Int1',
                },
                int2: {
                    'addURL': 'int2/add/',
                    'description': 'Int2 Description',
                    'iconSrc': 'data:test,int2',
                    'iconSrcSet': 'data:test,int2 1x, data:test,int2@2x 2x',
                    'id': 'int2',
                    'name': 'Int2',
                },
                int3: {
                    'addURL': 'int3/add/',
                    'description': 'Int3 Description',
                    'iconSrc': 'data:test,int3',
                    'iconSrcSet': 'data:test,int3 1x, data:test,int3@2x 2x',
                    'id': 'int3',
                    'name': 'Int3',
                },
            },
        });
        view.render();

        collection = view.list.collection;
    });

    describe('Configurations', function() {
        let $row1;
        let $row2;
        let $row3;
        let $row4;

        beforeEach(function() {
            const $rows = view.listView.$('tr');
            expect($rows.length).toBe(4);

            $row1 = $rows.eq(0);
            $row2 = $rows.eq(1);
            $row3 = $rows.eq(2);
            $row4 = $rows.eq(3);
        });

        describe('Rendering', function() {
            it('Icon', function() {
                const $icon1 =
                    $row1.find('.djblets-c-integration-config__name img');
                const $icon2 =
                    $row2.find('.djblets-c-integration-config__name img');
                const $icon3 =
                    $row3.find('.djblets-c-integration-config__name img');
                const $icon4 =
                    $row4.find('.djblets-c-integration-config__name img');

                expect($icon1.attr('src')).toBe('data:test,int1');
                expect($icon2.attr('src')).toBe('data:test,int2');
                expect($icon3.attr('src')).toBe('data:test,int3');
                expect($icon4.attr('src')).toBe('data:test,int1');

                expect($icon1.attr('srcset'))
                    .toBe('data:test,int1 1x, data:test,int1@2x 2x');
                expect($icon2.attr('srcset'))
                    .toBe('data:test,int2 1x, data:test,int2@2x 2x');
                expect($icon3.attr('srcset'))
                    .toBe('data:test,int3 1x, data:test,int3@2x 2x');
                expect($icon4.attr('srcset'))
                    .toBe('data:test,int1 1x, data:test,int1@2x 2x');
            });

            it('Name', function() {
                const $name1 =
                    $row1.find('.djblets-c-integration-config__name a');
                const $name2 =
                    $row2.find('.djblets-c-integration-config__name a');
                const $name3 =
                    $row3.find('.djblets-c-integration-config__name a');
                const $name4 =
                    $row4.find('.djblets-c-integration-config__name a');

                expect($name1.text()).toBe('Config 1');
                expect($name2.text()).toBe('Config 2');
                expect($name3.text()).toBe('Config 3');
                expect($name4.text()).toBe('Config 4');

                expect($name1.attr('href')).toBe('configs/1/');
                expect($name2.attr('href')).toBe('configs/2/');
                expect($name3.attr('href')).toBe('configs/3/');
                expect($name4.attr('href')).toBe('configs/4/');
            });

            it('Integration name', function() {
                const $intName1 = $row1.find(
                    '.djblets-c-integration-config__integration-name');
                const $intName2 = $row2.find(
                    '.djblets-c-integration-config__integration-name');
                const $intName3 = $row3.find(
                    '.djblets-c-integration-config__integration-name');
                const $intName4 = $row4.find(
                    '.djblets-c-integration-config__integration-name');

                expect($intName1.text().trim()).toBe('Int1');
                expect($intName2.text().trim()).toBe('Int2');
                expect($intName3.text().trim()).toBe('Int3');
                expect($intName4.text().trim()).toBe('Int1');
            });

            it('Status', function() {
                expect($row1.hasClass('-is-enabled')).toBe(true);
                expect($row2.hasClass('-is-enabled')).toBe(true);
                expect($row3.hasClass('-is-enabled')).toBe(false);
                expect($row4.hasClass('-is-enabled')).toBe(true);

                expect($row1.hasClass('-is-disabled')).toBe(false);
                expect($row2.hasClass('-is-disabled')).toBe(false);
                expect($row3.hasClass('-is-disabled')).toBe(true);
                expect($row4.hasClass('-is-disabled')).toBe(false);

                expect(
                    $row1.find('.djblets-c-config-forms-list__item-state')
                    .text()
                ).toBe('Enabled');

                expect(
                    $row2.find('.djblets-c-config-forms-list__item-state')
                    .text()
                ).toBe('Enabled');

                expect(
                    $row3.find('.djblets-c-config-forms-list__item-state')
                    .text()
                ).toBe('Disabled');

                expect(
                    $row4.find('.djblets-c-config-forms-list__item-state')
                    .text()
                ).toBe('Enabled');
            });
        });

        describe('Actions', function() {
            it('Delete', function() {
                const config = collection.at(0);

                spyOn(config, 'destroy').and.callThrough();
                spyOn(config, 'sync');

                spyOn($.fn, 'modalBox').and.callFake(
                    options => options.buttons[1].click());

                $row1.find('.config-forms-list-action-delete').click();

                expect($.fn.modalBox).toHaveBeenCalled();
                expect(config.destroy).toHaveBeenCalled();

                expect(collection.length).toBe(3);
                expect(view.listView.$('tr').length).toBe(3);
            });
        });
    });
});
