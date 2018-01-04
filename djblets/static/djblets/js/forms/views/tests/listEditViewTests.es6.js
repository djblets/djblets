suite('djblets/forms/views/ListEditView', () => {
    const addImgUrl = '/static/admin/img/icon_addlink.gif';
    const delImgUrl = '/static/admin/img/icon_deletelink.gif';

    /*
     * See templates/djblets_forms/list_edit_widget.html.
     */
    const formTemplate = _.template(dedent`
        <div class="list-edit-widget" id="<%- id %>_container">
         <ul>
         <% if (items.length > 0) { %>
          <% items.forEach(function(item, i) { %>
           <li class="list-edit-entry" data-list-index="<%- i %>">
            <input value="<%- item %>" type="text"<%- attrs %>>
            <a href="#" class="list-edit-remove-item">
             <img src="${delImgUrl}">
            </a>
           </li>
          <% }); %>
         <% } else { %>
           <li class="list-edit-entry" data-list-index="0">
            <input type="text">
            <a href="#" class="list-edit-remove-item">
             <img src="${delImgUrl}">
            </a>
           </li>
         <% } %>
          <li>
           <a href="#" class="list-edit-add-item"><img src="${addImgUrl}"></a>
          </li>
         </ul>
         <input id="<%- id %>" type="hidden"
                value="<%- nonZeroItems.join(',') %>">
        </div>
    `);

    const makeView = function makeView(items=[], attrs='') {
        attrs = attrs.length ? ` ${attrs}` : '';

        $testsScratch.append($(formTemplate({
            items: items,
            nonZeroItems: items.filter(i => (i.length > 0)),
            attrs: attrs,
            id: 'list-edit',
        })));

        const view = new Djblets.Forms.ListEditView({
            el: '#list-edit_container',
            inputAttrs: attrs,
            deleteImageUrl: delImgUrl,
            sep: ',',
        });

        view.render();

        return [view, view.$('#list-edit')];
    };

    describe('Updating fields', () => {
        it('With no values', () => {
            const [, $valueField] = makeView([]);
            expect($valueField.val()).toEqual('');
        });

        it('With one value', () => {
            const [view, $valueField] = makeView(['One']);

            expect($valueField.val()).toEqual('One');

            view.$('.list-edit-entry input').val('Foo').blur();
            expect($valueField.val()).toEqual('Foo');
        });

        it('With multiple values', () => {
            const [view, $valueField] = makeView(['one', 'two', 'three']);
            const $inputs = view.$('.list-edit-entry input');

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

    describe('Removal', () => {
        it('With no values', () => {
            const [view, $valueField] = makeView([]);

            expect($valueField.val()).toEqual('');
            expect(view.$('.list-edit-entry').length).toEqual(1);

            view.$('.list-edit-remove-item').click();
            expect($valueField.val()).toEqual('');
            expect(view.$('.list-edit-entry').length).toEqual(1);
        });

        it ('With one value', () => {
            const [view, $valueField] = makeView(['One']);
            expect($valueField.val()).toEqual('One');

            view.$('.list-edit-remove-item').click();
            expect($valueField.val()).toEqual('');
            expect(view.$('.list-edit-entry').length).toEqual(1);
        });

        it('With multiple values', () => {
            const [view, $valueField] = makeView(['One', 'Two', 'Three']);

            expect($valueField.val()).toEqual('One,Two,Three');

            view.$('.list-edit-remove-item').eq(1).click();
            expect($valueField.val()).toEqual('One,Three');
            expect(view.$('.list-edit-entry').length).toEqual(2);

            view.$('.list-edit-remove-item').eq(1).click();
            expect($valueField.val()).toEqual('One');
            expect(view.$('.list-edit-entry').length).toEqual(1);

            view.$('.list-edit-remove-item').click();
            expect($valueField.val()).toEqual('');
            expect(view.$('.list-edit-entry').length).toEqual(1);
        });
    });

    describe('Addition', () => {
        it('With values', () => {
            const [view, $valueField] = makeView(['one', 'two', 'three']);
            expect($valueField.val()).toEqual('one,two,three');

            view.$('.list-edit-add-item').click();
            expect($valueField.val()).toEqual('one,two,three');
            expect(view.$('.list-edit-entry').length).toEqual(4);

            view.$('.list-edit-entry input').eq(3).val('four').blur();
            expect($valueField.val()).toEqual('one,two,three,four');
        });

        it('With blank values', () => {
            const [view, $valueField] = makeView(['', '', '']);
            expect($valueField.val()).toEqual('');

            view.$('.list-edit-add-item').click();
            expect($valueField.val()).toEqual('');
            expect(view.$('.list-edit-entry').length).toEqual(4);

            view.$('.list-edit-entry input').eq(3).val('four').blur();
            expect($valueField.val()).toEqual('four');
        });

        it('With correct attributes', () => {
            const [view,] = makeView([], 'size="100" readonly');

            view.$('.list-edit-add-item').click();
            const $input = view.$('input').eq(1);
            expect($input.attr('size')).toEqual('100');
            expect($input.prop('readonly')).toBe(true);
        });
    });
});
