suite('djblets/forms/views/ListEditView', function() {
    /*
     * See templates/djblets_forms/list_edit_widget.html.
     */
    const formTemplate = _.template(dedent`
        <div class="djblets-c-list-edit-widget">
         <ul class="djblets-c-list-edit-widget__entries">
          <% if (items.length > 0) { %>
           <% items.forEach(function(item, i) { %>
            <li class="djblets-c-list-edit-widget__entry"
                data-list-index="<%- i %>">
             <input value="<%- item %>" type="text"<%= attrs %>>
             <a href="#" class="djblets-c-list-edit-widget__remove-item"></a>
            </li>
           <% }); %>
          <% } else { %>
           <li class="djblets-c-list-edit-widget__entry" data-list-index="0">
            <input type="text">
            <a href="#" class="djblets-c-list-edit-widget__remove-item"></a>
           </li>
          <% } %>
         </ul>
         <button class="djblets-c-list-edit-widget__add-item"></button>
         <input class="djblets-c-list-edit-widget__value"
                type="hidden" value="<%- nonZeroItems.join(',') %>">
        </div>
    `);

    const makeView = function makeView(items=[], attrs='') {
        attrs = attrs.length ? ` ${attrs}` : '';
        attrs = `${attrs} class="djblets-c-list-edit-widget__input"`;

        const $el =
            $(formTemplate({
                items: items,
                nonZeroItems: items.filter(i => (i.length > 0)),
                attrs: attrs,
            }))
            .appendTo($testsScratch);

        const view = new Djblets.Forms.ListEditView({
            el: $el,
            inputAttrs: attrs,
            sep: ',',
        });

        view.render();

        return [view, view.$('.djblets-c-list-edit-widget__value')];
    };

    describe('Updating fields', function() {
        it('With no values', function() {
            const [, $valueField] = makeView([]);
            expect($valueField.val()).toEqual('');
        });

        it('With one value', function() {
            const [view, $valueField] = makeView(['One']);

            expect($valueField.val()).toEqual('One');

            view.$('.djblets-c-list-edit-widget__input').val('Foo').blur();
            expect($valueField.val()).toEqual('Foo');
        });

        it('With multiple values', function() {
            const [view, $valueField] = makeView(['one', 'two', 'three']);
            const $inputs = view.$('.djblets-c-list-edit-widget__input');

            expect($valueField.val()).toEqual('one,two,three');

            $inputs.eq(2).val('baz').blur();
            expect($valueField.val()).toEqual('one,two,baz');

            $inputs.eq(0).val('').blur();
            expect($valueField.val()).toEqual('two,baz');

            $inputs.eq(1).val('').blur();
            expect($valueField.val()).toEqual('baz');

            $inputs.eq(2).val('').blur();
            expect($valueField.val()).toEqual('');
        });
    });

    describe('Removal', function() {
        it('With no values', function() {
            const [view, $valueField] = makeView([]);

            expect($valueField.val()).toEqual('');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);

            view.$('.djblets-c-list-edit-widget__remove-item').click();
            expect($valueField.val()).toEqual('');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);
        });

        it ('With one value', function() {
            const [view, $valueField] = makeView(['One']);
            expect($valueField.val()).toEqual('One');

            view.$('.djblets-c-list-edit-widget__remove-item').click();
            expect($valueField.val()).toEqual('');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);
        });

        it('With multiple values', function() {
            const [view, $valueField] = makeView(['One', 'Two', 'Three']);

            expect($valueField.val()).toEqual('One,Two,Three');

            expect(view.$('.djblets-c-list-edit-widget__remove-item').length)
                .toEqual(3);

            view.$('.djblets-c-list-edit-widget__remove-item').eq(1).click();
            expect($valueField.val()).toEqual('One,Three');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(2);
            expect(view.$('.djblets-c-list-edit-widget__remove-item').length)
                .toEqual(2);

            view.$('.djblets-c-list-edit-widget__remove-item').eq(1).click();
            expect($valueField.val()).toEqual('One');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);
            expect(view.$('.djblets-c-list-edit-widget__remove-item').length)
                .toEqual(1);

            view.$('.djblets-c-list-edit-widget__remove-item').click();
            expect($valueField.val()).toEqual('');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(1);
        });
    });

    describe('Addition', function() {
        it('With values', function() {
            const [view, $valueField] = makeView(['one', 'two', 'three']);
            expect($valueField.val()).toEqual('one,two,three');

            view.$('.djblets-c-list-edit-widget__add-item').click();
            expect($valueField.val()).toEqual('one,two,three');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(4);

            view.$('.djblets-c-list-edit-widget__input').eq(3)
                .val('four')
                .blur();
            expect($valueField.val()).toEqual('one,two,three,four');
        });

        it('With blank values', function() {
            const [view, $valueField] = makeView(['', '', '']);
            expect($valueField.val()).toEqual('');

            view.$('.djblets-c-list-edit-widget__add-item').click();
            expect($valueField.val()).toEqual('');
            expect(view.$('.djblets-c-list-edit-widget__entry').length)
                .toEqual(4);

            view.$('.djblets-c-list-edit-widget__input').eq(3)
                .val('four')
                .blur();
            expect($valueField.val()).toEqual('four');
        });

        it('With correct attributes', function() {
            const [view,] = makeView([], 'size="100" readonly');

            view.$('.djblets-c-list-edit-widget__add-item').click();
            const $input = view.$('input').eq(1);
            expect($input.attr('size')).toEqual('100');
            expect($input.prop('readonly')).toBe(true);
        });
    });
});
