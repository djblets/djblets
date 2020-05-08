suite('djblets/forms/models/ConditionChoice', function() {
    describe('Initialization', function() {
        it('With parse and data', function() {
            const choice = new Djblets.Forms.ConditionChoice({
                id: 'my-choice',
                name: 'My Choice',
                valueField: {
                    model: {
                        className: 'Djblets.Forms.ConditionValueField',
                        data: {
                            myModelKey: 'my-value'
                        }
                    },
                    view: {
                        className: 'Djblets.Forms.ConditionValueFormFieldView',
                        data: {
                            myViewKey: 'my-value'
                        }
                    }
                },
                operators: [
                    {
                        id: 'my-op',
                        name: 'My Op',
                        useValue: false
                    }
                ]
            }, {
                parse: true
            });

            expect(choice.id).toBe('my-choice');
            expect(choice.get('name')).toBe('My Choice');
            expect(choice.get('valueField')).toEqual({
                modelClass: Djblets.Forms.ConditionValueField,
                modelData: {
                    myModelKey: 'my-value'
                },
                viewClass: Djblets.Forms.ConditionValueFormFieldView,
                viewData: {
                    myViewKey: 'my-value'
                }
            });
            expect(choice.operators.length).toBe(1);

            const op = choice.operators.at(0);
            expect(op.id).toBe('my-op');
            expect(op.get('name')).toBe('My Op');
            expect(op.get('useValue')).toBe(false);
        });
    });

    describe('Methods', function() {
        it('createValueField', function() {
            const choice = new Djblets.Forms.ConditionChoice({
                id: 'my-choice',
                name: 'My Choice',
                valueField: {
                    modelClass: Djblets.Forms.ConditionValueField,
                    modelData: {
                        myModelKey: 'my-value'
                    },
                    viewClass: Djblets.Forms.ConditionValueFormFieldView,
                    viewData: {
                        myViewKey: 'my-value'
                    }
                }
            });

            const valueField = choice.createValueField('my-field');
            expect(valueField.model.get('fieldName')).toBe('my-field');
        });
    });
});
