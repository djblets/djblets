suite('djblets/forms/models/ConditionOperator', function() {
    describe('Initialization', function() {
        it('With parse and data', function() {
            const op = new Djblets.Forms.ConditionOperator({
                id: 'my-op',
                name: 'My Operator',
                useValue: true,
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
                }
            }, {
                parse: true
            });

            expect(op.id).toBe('my-op');
            expect(op.get('name')).toBe('My Operator');
            expect(op.get('useValue')).toBe(true);
            expect(op.get('valueField')).toEqual({
                modelClass: Djblets.Forms.ConditionValueField,
                modelData: {
                    myModelKey: 'my-value'
                },
                viewClass: Djblets.Forms.ConditionValueFormFieldView,
                viewData: {
                    myViewKey: 'my-value'
                }
            });
        });

        it('With parse and data, but no valueField', function() {
            const op = new Djblets.Forms.ConditionOperator({
                id: 'my-op',
                name: 'My Operator',
                useValue: true
            }, {
                parse: true
            });

            expect(op.id).toBe('my-op');
            expect(op.get('name')).toBe('My Operator');
            expect(op.get('valueField')).toBe(null);
            expect(op.get('useValue')).toBe(true);
        });
    });

    describe('createValueField', function() {
        it('With custom valueField', function() {
            const op = new Djblets.Forms.ConditionOperator({
                id: 'my-op',
                name: 'My Operator',
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

            const valueField = op.createValueField('my-field');
            expect(valueField.model.get('fieldName')).toBe('my-field');
        });

        it('Without custom valueField', function() {
            const op = new Djblets.Forms.ConditionOperator({
                id: 'my-op',
                name: 'My Operator'
            });

            expect(() => op.createValueField('my-field')).toThrowError(
                'This operator does not have a custom valueField.');
        });
    });
});
