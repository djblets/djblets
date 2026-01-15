suite('djblets/forms/views/ListEditView', function() {

    const formTemplate = _.template(dedent`
    <div class="djblets-c-list-edit-widget list-edit-widget">
    <input type="hidden" name="_num_rows" value="<%- renderedRows.length %>">
      <ul class="djblets-c-list-edit-widget__entries">
      <% if (renderedRows.length > 0) { %>
        <% renderedRows.forEach(function(row, i) { %>
        <li class="djblets-c-list-edit-widget__entry"
            data-list-index="<%- i %>">
        <%= row %>
        <a href="#" class="djblets-c-list-edit-widget__remove-item"
            role="button">
        <span class="fa fa-times"></span>
        </a>
        </li>
      <% }); %>
      <% } else { %>
        <li class="djblets-c-list-edit-widget__entry" data-list-index="0">
        <%= renderedDefaultRow %>
        <a href="#" class="djblets-c-list-edit-widget__remove-item"></a>
        </li>
      <% } %>
      </ul>
     <button class="djblets-c-list-edit-widget__add-item btn" role="button">
     <span class="fa fa-plus"></span>
     </button>
    </div>
    `);

    const makeView = function makeView(
        renderedRows=[],
        renderedDefaultRow=dedent`
            <input type="text"
                class="djblets-c-list-edit-widget__input"
                id="_value___EDIT_LIST_ROW_ID__"
                name="_value[__EDIT_LIST_ROW_INDEX__]">
        `,
    ) {
        const $el =
            $(formTemplate({
                renderedDefaultRow: renderedDefaultRow
                    .replaceAll('__EDIT_LIST_ROW_ID__', '0')
                    .replaceAll('__EDIT_LIST_ROW_INDEX__', '0'),
                renderedRows: renderedRows,
            }))
            .appendTo($testsScratch);

        const view = new Djblets.Forms.ListEditView({
            el: $el,
            fieldName: '',
            removeText: 'Remove this item.',
            renderedDefaultRow: renderedDefaultRow,
        });

        view.render();

        return [view, view.$('input[name="_num_rows"]')];
    };

    describe('Removal', function() {
        it('With no values', function() {
            const [view, $numRows] = makeView([]);

            expect($numRows.val()).toEqual('1');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);

            let $input = view.$('.djblets-c-list-edit-widget__input');
            expect($input.val()).toEqual('');
            expect($input.attr('id')).toEqual('_value_0');
            expect($input.attr('name')).toEqual('_value[0]');

            /* Remove the item. */
            view.$('.djblets-c-list-edit-widget__remove-item').click();

            expect($numRows.val()).toEqual('1');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);

            $input = view.$('.djblets-c-list-edit-widget__input');
            expect($input.val()).toEqual('');
            expect($input.attr('id'))
                .toMatch(/^_value_djblets-list-edit-row\d+/);
            expect($input.attr('name')).toEqual('_value[0]');
        });

        it('With one value', function() {
            const [view, $numRows] = makeView([
                dedent`
                    <input type="text"
                           class="djblets-c-list-edit-widget__input"
                           id="_value_UUID"
                           name="_value[0]"
                           value="One">
                `,
            ]);
            expect($numRows.val()).toEqual('1');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);

            let $input = view.$('.djblets-c-list-edit-widget__input');
            expect($input.val()).toEqual('One');
            expect($input.attr('id')).toEqual('_value_UUID');
            expect($input.attr('name')).toEqual('_value[0]');

            /* Remove the item. */
            view.$('.djblets-c-list-edit-widget__remove-item').click();

            expect($numRows.val()).toEqual('1');

            $input = view.$('.djblets-c-list-edit-widget__input');
            expect($input.val()).toEqual('');
            expect($input.attr('id'))
                .toMatch(/^_value_djblets-list-edit-row\d+/);
            expect($input.attr('name')).toEqual('_value[0]');
        });

        it('With multiple values', function() {
            const [view, $numRows] = makeView([
                dedent`
                    <input type="text"
                           class="djblets-c-list-edit-widget__input"
                           id="_value_UUID1"
                           name="_value[0]"
                           value="One">
                `,
                dedent`
                    <input type="text"
                           class="djblets-c-list-edit-widget__input"
                           id="_value_UUID2"
                           name="_value[1]"
                           value="Two">
                `,
                dedent`
                    <input type="text"
                           class="djblets-c-list-edit-widget__input"
                           id="_value_UUID3"
                           name="_value[2]"
                           value="Three">
                `,
            ]);

            expect($numRows.val()).toEqual('3');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(3);
            expect(view.$('.djblets-c-list-edit-widget__remove-item').length)
                .toEqual(3);

            let $inputOne = view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('One');
            expect($inputOne.attr('id')).toEqual('_value_UUID1');
            expect($inputOne.attr('name')).toEqual('_value[0]');

            let $inputTwo = view.$('.djblets-c-list-edit-widget__input').eq(1);
            expect($inputTwo.val()).toEqual('Two');
            expect($inputTwo.attr('id')).toEqual('_value_UUID2');
            expect($inputTwo.attr('name')).toEqual('_value[1]');

            const $inputThree =
                view.$('.djblets-c-list-edit-widget__input').eq(2);
            expect($inputThree.val()).toEqual('Three');
            expect($inputThree.attr('id')).toEqual('_value_UUID3');
            expect($inputThree.attr('name')).toEqual('_value[2]');

            /* Remove Item 2. */
            view.$('.djblets-c-list-edit-widget__remove-item').eq(1).click();

            expect($numRows.val()).toEqual('2');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(2);
            expect(view.$('.djblets-c-list-edit-widget__remove-item').length)
                .toEqual(2);

            $inputOne = view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('One');
            expect($inputOne.attr('id')).toEqual('_value_UUID1');
            expect($inputOne.attr('name')).toEqual('_value[0]');

            $inputTwo = view.$('.djblets-c-list-edit-widget__input').eq(1);
            expect($inputTwo.val()).toEqual('Three');
            expect($inputTwo.attr('id')).toEqual('_value_UUID3');
            expect($inputTwo.attr('name')).toEqual('_value[1]');

            /* Remove Item 3. */
            view.$('.djblets-c-list-edit-widget__remove-item').eq(1).click();

            expect($numRows.val()).toEqual('1');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);
            expect(view.$('.djblets-c-list-edit-widget__remove-item').length)
                .toEqual(1);

            $inputOne = view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('One');
            expect($inputOne.attr('id')).toEqual('_value_UUID1');
            expect($inputOne.attr('name')).toEqual('_value[0]');

            /* Remove Item 1. */
            view.$('.djblets-c-list-edit-widget__remove-item').click();
            expect($numRows.val()).toEqual('1');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);

            $inputOne = view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('');
            expect($inputOne.attr('id'))
                .toMatch(/^_value_djblets-list-edit-row\d+/);
            expect($inputOne.attr('name')).toEqual('_value[0]');
        });
    });

    describe('Addition', function() {
        it('With values', function() {
            const [view, $numRows] = makeView([
                dedent`
                    <input type="text"
                           class="djblets-c-list-edit-widget__input"
                           id="_value_UUID1",
                           name="_value[0]"
                           value="One">
                `,
                dedent`
                    <input type="text"
                           class="djblets-c-list-edit-widget__input"
                           id="_value_UUID2",
                           name="_value[1]"
                           value="Two">
                `,
                dedent`
                    <input type="text"
                           class="djblets-c-list-edit-widget__input"
                           id="_value_UUID3",
                           name="_value[2]"
                           value="Three">
                `,
            ]);

            /* Add an item. */
            view.$('.djblets-c-list-edit-widget__add-item').click();

            expect($numRows.val()).toEqual('4');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(4);

            const $inputOne =
                view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('One');
            expect($inputOne.attr('id')).toEqual('_value_UUID1');
            expect($inputOne.attr('name')).toEqual('_value[0]');

            const $inputTwo =
                view.$('.djblets-c-list-edit-widget__input').eq(1);
            expect($inputTwo.val()).toEqual('Two');
            expect($inputTwo.attr('id')).toEqual('_value_UUID2');
            expect($inputTwo.attr('name')).toEqual('_value[1]');

            const $inputThree =
                view.$('.djblets-c-list-edit-widget__input').eq(2);
            expect($inputThree.val()).toEqual('Three');
            expect($inputThree.attr('id')).toEqual('_value_UUID3');
            expect($inputThree.attr('name')).toEqual('_value[2]');

            const $inputFour =
                view.$('.djblets-c-list-edit-widget__input').eq(3);
            expect($inputFour.val()).toEqual('');
            expect($inputFour.attr('id'))
                .toMatch(/^_value_djblets-list-edit-row\d+/);
            expect($inputFour.attr('name')).toEqual('_value[3]');
        });

        it('With no values', function() {
            const [view, $numRows] = makeView([]);

            /* Add an item. */
            view.$('.djblets-c-list-edit-widget__add-item').click();

            expect($numRows.val()).toEqual('2');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(2);

            const $inputOne =
                view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('');
            expect($inputOne.attr('id')).toEqual('_value_0');
            expect($inputOne.attr('name')).toEqual('_value[0]');

            const $inputTwo =
                view.$('.djblets-c-list-edit-widget__input').eq(1);
            expect($inputTwo.val()).toEqual('');
            expect($inputTwo.attr('id'))
                .toMatch(/^_value_djblets-list-edit-row\d+/);
            expect($inputTwo.attr('name')).toEqual('_value[1]');
        });
    });
});
