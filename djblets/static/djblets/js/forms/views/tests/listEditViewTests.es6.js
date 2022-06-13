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

    const makeView = function makeView(renderedRows=[],
        renderedDefaultRow=dedent`<input type="text"
            class="djblets-c-list-edit-widget__input"
            name="_value[0]" />`) {
        const $el =
            $(formTemplate({
                renderedRows: renderedRows,
                renderedDefaultRow: renderedDefaultRow,
            }))
            .appendTo($testsScratch);

        const view = new Djblets.Forms.ListEditView({
            el: $el,
            renderedDefaultRow: renderedDefaultRow,
            fieldName: '',
            removeText: 'Remove this item.',
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
            expect(view.$('.djblets-c-list-edit-widget__input').val())
                .toEqual('');
            expect(view.$('.djblets-c-list-edit-widget__input').attr('name'))
                .toEqual('_value[0]');

            view.$('.djblets-c-list-edit-widget__remove-item').click();
            expect($numRows.val()).toEqual('1');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);
            expect(view.$('.djblets-c-list-edit-widget__input').val())
                .toEqual('');
            expect(view.$('.djblets-c-list-edit-widget__input').attr('name'))
                .toEqual('_value[0]');
        });

        it ('With one value', function() {
            const [view, $numRows] = makeView([
                dedent`<input type="text"
                class="djblets-c-list-edit-widget__input"
                name="_value[0]"
                value="One" />`,
            ]);
            expect($numRows.val()).toEqual('1');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);
            expect(view.$('.djblets-c-list-edit-widget__input').val())
                .toEqual('One');
            expect(view.$('.djblets-c-list-edit-widget__input').attr('name'))
                .toEqual('_value[0]');

            view.$('.djblets-c-list-edit-widget__remove-item').click();
            expect($numRows.val()).toEqual('1');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);
            expect(view.$('.djblets-c-list-edit-widget__input').val())
                .toEqual(''); // this might not work? val might not even be there
            expect(view.$('.djblets-c-list-edit-widget__input').attr('name'))
                .toEqual('_value[0]');
        });

        it('With multiple values', function() {
            const [view, $numRows] = makeView([
                dedent`<input type="text"
                class="djblets-c-list-edit-widget__input"
                name="_value[0]"
                value="One" />`,
                dedent`<input type="text"
                class="djblets-c-list-edit-widget__input"
                name="_value[1]"
                value="Two" />`,
                dedent`<input type="text"
                class="djblets-c-list-edit-widget__input"
                name="_value[2]"
                value="Three" />`,
            ]);

            expect($numRows.val()).toEqual('3');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(3);
            expect(view.$('.djblets-c-list-edit-widget__remove-item').length)
                .toEqual(3);
            let $inputOne = view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('One');
            expect($inputOne.attr('name')).toEqual('_value[0]');
            let $inputTwo = view.$('.djblets-c-list-edit-widget__input').eq(1);
            expect($inputTwo.val()).toEqual('Two');
            expect($inputTwo.attr('name')).toEqual('_value[1]');
            let $inputThree = view.$('.djblets-c-list-edit-widget__input').eq(2);
            expect($inputThree.val()).toEqual('Three');
            expect($inputThree.attr('name')).toEqual('_value[2]');

            view.$('.djblets-c-list-edit-widget__remove-item').eq(1).click();
            expect($numRows.val()).toEqual('2');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(2);
            expect(view.$('.djblets-c-list-edit-widget__remove-item').length)
                .toEqual(2);
            $inputOne = view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('One');
            expect($inputOne.attr('name')).toEqual('_value[0]');
            $inputTwo = view.$('.djblets-c-list-edit-widget__input').eq(1);
            expect($inputTwo.val()).toEqual('Three');
            expect($inputTwo.attr('name')).toEqual('_value[1]');

            view.$('.djblets-c-list-edit-widget__remove-item').eq(1).click();
            expect($numRows.val()).toEqual('1');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);
            expect(view.$('.djblets-c-list-edit-widget__remove-item').length)
                .toEqual(1);
            $inputOne = view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('One');
            expect($inputOne.attr('name')).toEqual('_value[0]');

            view.$('.djblets-c-list-edit-widget__remove-item').click();
            expect($numRows.val()).toEqual('1');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);
            $inputOne = view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('');
            expect($inputOne.attr('name')).toEqual('_value[0]');
        });
    });

    describe('Addition', function() {
        it('With values', function() {
            const [view, $numRows] = makeView([
                dedent`<input type="text"
                class="djblets-c-list-edit-widget__input"
                name="_value[0]"
                value="One" />`,
                dedent`<input type="text"
                class="djblets-c-list-edit-widget__input"
                name="_value[1]"
                value="Two" />`,
                dedent`<input type="text"
                class="djblets-c-list-edit-widget__input"
                name="_value[2]"
                value="Three" />`,
            ]);

            view.$('.djblets-c-list-edit-widget__add-item').click();
            expect($numRows.val()).toEqual('4');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(4);
            let $inputOne = view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('One');
            expect($inputOne.attr('name')).toEqual('_value[0]');
            let $inputTwo = view.$('.djblets-c-list-edit-widget__input').eq(1);
            expect($inputTwo.val()).toEqual('Two');
            expect($inputTwo.attr('name')).toEqual('_value[1]');
            let $inputThree = view.$('.djblets-c-list-edit-widget__input').eq(2);
            expect($inputThree.val()).toEqual('Three');
            expect($inputThree.attr('name')).toEqual('_value[2]');
            let $inputFour = view.$('.djblets-c-list-edit-widget__input').eq(3);
            expect($inputFour.val()).toEqual('');
            expect($inputFour.attr('name')).toEqual('_value[3]');
        });

        it('With no values', function() {
            const [view, $numRows] = makeView([]);

            view.$('.djblets-c-list-edit-widget__add-item').click();
            expect($numRows.val()).toEqual('2');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(2);
            let $inputOne = view.$('.djblets-c-list-edit-widget__input').eq(0);
            expect($inputOne.val()).toEqual('');
            expect($inputOne.attr('name')).toEqual('_value[0]');
            let $inputTwo = view.$('.djblets-c-list-edit-widget__input').eq(1);
            expect($inputTwo.val()).toEqual('');
            expect($inputTwo.attr('name')).toEqual('_value[1]');
        });
    });
});
