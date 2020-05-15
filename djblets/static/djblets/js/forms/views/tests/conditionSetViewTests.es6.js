suite('djblets/forms/views/ConditionValueFormFieldView', function() {
    function makeValueField(html) {
        return {
            model: {
                className: 'Djblets.Forms.ConditionValueField',
                data: {
                    fieldHTML: html
                }
            },
            view: {
                className: 'Djblets.Forms.ConditionValueFormFieldView'
            }
        };
    }

    function setupConditionSetView(conditionsData) {
        const conditionsTemplate = _.template([
            '<div class="conditions-field">\n',
            ' <input type="hidden" name="my_conditions_last_id" />\n',
            ' <div class="conditions-field-mode"></div>\n',
            ' <div class="conditions-field-rows-container">\n',
            '  <ul class="conditions-field-rows"></ul>\n',
            '  <a href="#" class="conditions-field-add-condition"></a>\n',
            ' </div>\n',
            '</div>'
        ].join(''));

        const conditionSetView = new Djblets.Forms.ConditionSetView({
            el: $(conditionsTemplate()),
            model: new Djblets.Forms.ConditionSet({
                fieldName: 'my_conditions',
                choicesData: [
                    {
                        id: 'my-choice-1',
                        name: 'My Choice 1',
                        valueField: makeValueField('<input type="text" />'),
                        operators: [
                            {
                                id: 'my-op-1',
                                name: 'My Op 1',
                                useValue: true
                            },
                            {
                                id: 'my-op-2',
                                name: 'My Op 2',
                                useValue: true,
                                valueField: makeValueField('<input type="number" />')
                            }
                        ]
                    },
                    {
                        id: 'my-choice-2',
                        name: 'My Choice 2',
                        valueField: makeValueField('<input type="email" />'),
                        operators: [
                            {
                                id: 'my-op-3',
                                name: 'My Op 3',
                                useValue: true
                            },
                            {
                                id: 'my-op-4',
                                name: 'My Op 4',
                                useValue: true
                            }
                        ]
                    }
                ],
                conditionsData: conditionsData
            }, {
                parse: true
            })
        });

        conditionSetView.render();

        return conditionSetView;
    }

    describe('Rendering', function() {
        it('Loaded rows', function() {
            const conditionSetView = setupConditionSetView([
                {
                    choiceID: 'my-choice-1',
                    operatorID: 'my-op-1',
                    value: '<test>',
                    valid: true
                },
                {
                    choiceID: 'my-choice-2',
                    operatorID: 'my-op-4',
                    value: 42,
                    valid: true
                }
            ]);

            const $rows = conditionSetView.$('.conditions-field-row');
            expect($rows.length).toBe(2);

            const $lastID =
                conditionSetView.$('input[name=my_conditions_last_id]');
            expect($lastID.val()).toBe('1');

            /* Check the first row. */
            let $row = $rows.eq(0);
            let $choice = $row.find('.conditions-field-choice');
            expect($choice.html()).toBe([
                '<select name="my_conditions_choice[0]">',
                '<option value="my-choice-1">My Choice 1</option>',
                '<option value="my-choice-2">My Choice 2</option>',
                '</select>'
            ].join(''));
            expect($choice.children('select').val()).toBe('my-choice-1');

            let $operator = $row.find('.conditions-field-operator');
            expect($operator.html()).toBe([
                '<select name="my_conditions_operator[0]">',
                '<option value="my-op-1">My Op 1</option>',
                '<option value="my-op-2">My Op 2</option>',
                '</select>'
            ].join(''));
            expect($operator.children('select').val()).toBe('my-op-1');

            let $value = $row.find('.conditions-field-value');
            let $input = $value.find('input');
            expect($input.parent().prop('tagName')).toBe('SPAN');
            expect($input.attr('type')).toBe('text');
            expect($input.attr('name')).toBe('my_conditions_value[0]');
            expect($input.val()).toBe('<test>');

            /* Check the second row. */
            $row = $rows.eq(1);
            $choice = $row.find('.conditions-field-choice');
            expect($choice.html()).toBe([
                '<select name="my_conditions_choice[1]">',
                '<option value="my-choice-1">My Choice 1</option>',
                '<option value="my-choice-2">My Choice 2</option>',
                '</select>'
            ].join(''));
            expect($choice.children('select').val()).toBe('my-choice-2');

            $operator = $row.find('.conditions-field-operator');
            expect($operator.html()).toBe([
                '<select name="my_conditions_operator[1]">',
                '<option value="my-op-3">My Op 3</option>',
                '<option value="my-op-4">My Op 4</option>',
                '</select>'
            ].join(''));
            expect($operator.children('select').val()).toBe('my-op-4');

            $value = $row.find('.conditions-field-value');
            $input = $value.find('input');
            expect($input.parent().prop('tagName')).toBe('SPAN');
            expect($input.attr('type')).toBe('email');
            expect($input.attr('name')).toBe('my_conditions_value[1]');
            expect($input.val()).toBe('42');
        });

        it('Loaded rows with errors', function() {
            const conditionSetView = setupConditionSetView([
                {
                    choiceID: 'my-choice-1',
                    operatorID: 'my-op-1',
                    value: '<test>',
                    error: 'This is an <error>.',
                    valid: true
                }
            ]);

            const $rows = conditionSetView.$('.conditions-field-row');
            expect($rows.length).toBe(1);

            const $lastID =
                conditionSetView.$('input[name=my_conditions_last_id]');
            expect($lastID.val()).toBe('0');

            const $row = $rows.eq(0);
            const $error = $row.find('.error-list li');
            expect($error.length).toBe(1);
            expect($error.html()).toBe('This is an &lt;error&gt;.');
        });
    });

    describe('Actions', function() {
        it('Add a new condition', function() {
            const conditionSetView = setupConditionSetView();

            let $rows = conditionSetView.$('.conditions-field-row');
            expect($rows.length).toBe(0);

            const $lastID =
                conditionSetView.$('input[name=my_conditions_last_id]');
            expect($lastID.val()).toBe('');

            spyOn(conditionSetView.model, 'addNewCondition').and.callThrough();
            conditionSetView.$('.conditions-field-add-condition').click();
            expect(conditionSetView.model.addNewCondition).toHaveBeenCalled();

            $rows = conditionSetView.$('.conditions-field-row');
            expect($rows.length).toBe(1);
            expect($lastID.val()).toBe('0');

            const $row = $rows.eq(0);
            const $choice = $row.find('.conditions-field-choice');
            expect($choice.html()).toBe([
                '<select name="my_conditions_choice[0]">',
                '<option value="my-choice-1">My Choice 1</option>',
                '<option value="my-choice-2">My Choice 2</option>',
                '</select>'
            ].join(''));
            expect($choice.children('select').val()).toBe('my-choice-1');

            const $operator = $row.find('.conditions-field-operator');
            expect($operator.html()).toBe([
                '<select name="my_conditions_operator[0]">',
                '<option value="my-op-1">My Op 1</option>',
                '<option value="my-op-2">My Op 2</option>',
                '</select>'
            ].join(''));
            expect($operator.children('select').val()).toBe('my-op-1');

            const $value = $row.find('.conditions-field-value');
            const $input = $value.find('input');
            expect($input.parent().prop('tagName')).toBe('SPAN');
            expect($input.attr('type')).toBe('text');
            expect($input.attr('name')).toBe('my_conditions_value[0]');
            expect($input.val()).toBe('');
        });

        it('Delete a condition', function() {
            const conditionSetView = setupConditionSetView([
                {
                    choiceID: 'my-choice-1',
                    operatorID: 'my-op-1',
                    value: '<test>',
                    valid: true
                }
            ]);

            let $rows = conditionSetView.$('.conditions-field-row');
            expect(conditionSetView.model.conditions.length).toBe(1);
            expect($rows.length).toBe(1);

            const $lastID =
                conditionSetView.$('input[name=my_conditions_last_id]');
            expect($lastID.val()).toBe('0');

            const condition = conditionSetView.model.conditions.at(0);

            spyOn(condition, 'destroy').and.callThrough();
            $rows.eq(0).find('.conditions-field-row-delete').click();
            expect(condition.destroy).toHaveBeenCalled();

            $rows = conditionSetView.$('.conditions-field-row');
            expect(conditionSetView.model.conditions.length).toBe(0);
            expect($rows.length).toBe(0);

            /*
             * The last ID remains the same during deletions. It's not a row
             * counter.
             */
            expect($lastID.val()).toBe('0');
        });

        it('Changing a choice updates model', function() {
            const conditionSetView = setupConditionSetView([
                {
                    choiceID: 'my-choice-1',
                    operatorID: 'my-op-1',
                    value: '<test>',
                    valid: true
                }
            ]);

            const $rows = conditionSetView.$('.conditions-field-row');
            const condition = conditionSetView.model.conditions.at(0);

            $rows.eq(0).find('.conditions-field-choice select')
                .val('my-choice-2')
                .trigger('change');

            expect(condition.get('choice').id).toBe('my-choice-2');
        });

        it('Changing an operator updates model', function() {
            const conditionSetView = setupConditionSetView([
                {
                    choiceID: 'my-choice-1',
                    operatorID: 'my-op-1',
                    value: '<test>',
                    valid: true
                }
            ]);

            const $rows = conditionSetView.$('.conditions-field-row');
            const condition = conditionSetView.model.conditions.at(0);

            $rows.eq(0).find('.conditions-field-operator select')
                .val('my-op-2')
                .trigger('change');

            expect(condition.get('operator').id).toBe('my-op-2');
        });
    });

    describe('Model events', function() {
        let conditionSetView,
            conditionSet,
            condition,
            $row,
            $choice,
            $operator,
            $valueWrapper;

        beforeEach(function() {
            conditionSetView = setupConditionSetView([
                {
                    choiceID: 'my-choice-1',
                    operatorID: 'my-op-1',
                    value: '<test>',
                    valid: true
                }
            ]);

            conditionSet = conditionSetView.model;

            condition = conditionSet.conditions.at(0);
            $row = conditionSetView.$('.conditions-field-row').eq(0);
            $choice = $row.find('.conditions-field-choice select');
            $operator = $row.find('.conditions-field-operator select');
            $valueWrapper = $row.find('.conditions-field-value');

            const $input = $valueWrapper.find('input');
            expect($input.attr('type')).toBe('text');
            expect($input.val()).toBe('<test>');
        });

        describe('Choice changed', function() {
            it('Updates UI state', function() {
                condition.set('choice',
                              conditionSet.choices.get('my-choice-2'));

                expect($choice.val()).toBe('my-choice-2');
                expect($operator.val()).toBe('my-op-3');

                const $input = $valueWrapper.find('input');
                expect($input.attr('type')).toBe('email');
                expect($input.val()).toBe('');
            });
        });

        describe('Operator changed', function() {
            it('Updates UI state', function() {
                const choice = conditionSet.choices.get('my-choice-1');
                condition.set('operator', choice.operators.get('my-op-2'));

                expect($choice.val()).toBe('my-choice-1');
                expect($operator.val()).toBe('my-op-2');

                const $input = $valueWrapper.find('input');
                expect($input.attr('type')).toBe('number');
                expect($input.val()).toBe('');
            });

            it('Retains value if valueField remains', function() {
                const choice = conditionSet.choices.get('my-choice-2');

                /* Set the initial conditions. */
                condition.set('choice', choice);
                $valueWrapper.find('input').val('42');
                expect($operator.val()).toBe('my-op-3');

                /* Trigger the operator change. */
                condition.set('operator', choice.operators.get('my-op-4'));

                expect($valueWrapper.find('input').val()).toBe('42');
            });
        });

        describe('Value changed', function() {
            it('Updated UI state', function() {
                condition.set('value', 'new-value');

                expect($valueWrapper.find('input').val()).toBe('new-value');
            });
        });
    });
});
