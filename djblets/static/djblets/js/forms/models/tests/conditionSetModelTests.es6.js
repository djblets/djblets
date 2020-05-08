suite('djblets/forms/models/ConditionSet', function() {
    describe('Initialization', function() {
        it('choicesData parsed', function() {
            const conditionSet = new Djblets.Forms.ConditionSet({
                fieldName: 'my-conditions',
                choicesData: [{
                    id: 'my-choice',
                    name: 'My Choice'
                }]
            });

            expect(conditionSet.choices.length).toBe(1);
            expect(conditionSet.choices.at(0).id).toBe('my-choice');
            expect(conditionSet.get('lastID')).toBe(null);
        });

        it('conditionsData parsed', function() {
            const conditionSet = new Djblets.Forms.ConditionSet({
                choicesData: [{
                    id: 'my-choice',
                    name: 'My Choice',
                    operators: [
                        {
                            id: 'my-op-1',
                            name: 'My Op 1'
                        },
                        {
                            id: 'my-op-2',
                            name: 'My Op 2'
                        }
                    ]
                }],
                conditionsData: [
                    {
                        choiceID: 'my-choice',
                        operatorID: 'my-op-1',
                        value: 'abc123',
                        valid: false,
                        error: 'My error'
                    },
                    {
                        choiceID: 'my-choice',
                        operatorID: 'my-op-2',
                        value: 42,
                        valid: true
                    }
                ]
            });

            const conditions = conditionSet.conditions;
            expect(conditions.length).toBe(2);

            let condition = conditions.at(0);
            expect(condition.id).toBe(0);
            expect(condition.get('choice').id).toBe('my-choice');
            expect(condition.get('operator').id).toBe('my-op-1');
            expect(condition.get('value')).toBe('abc123');
            expect(condition.get('valid')).toBe(false);
            expect(condition.get('error')).toBe('My error');

            condition = conditions.at(1);
            expect(condition.id).toBe(1);
            expect(condition.get('choice').id).toBe('my-choice');
            expect(condition.get('operator').id).toBe('my-op-2');
            expect(condition.get('value')).toBe(42);
            expect(condition.get('valid')).toBe(true);
            expect(condition.get('error')).toBe(null);

            expect(conditionSet.get('lastID')).toBe(1);
        });

        it('conditionsData parsed with bad choiceID', function() {
            const conditionSet = new Djblets.Forms.ConditionSet({
                choicesData: [{
                    id: 'my-choice',
                    name: 'My Choice',
                    operators: [
                        {
                            id: 'my-op-1',
                            name: 'My Op 1'
                        },
                        {
                            id: 'my-op-2',
                            name: 'My Op 2'
                        }
                    ]
                }],
                conditionsData: [
                    {
                        choiceID: 'invalid-choice',
                        operatorID: 'my-op-1',
                        value: 'abc123',
                        valid: false,
                        error: 'My error'
                    }
                ]
            });

            const conditions = conditionSet.conditions;
            expect(conditions.length).toBe(1);

            const condition = conditions.at(0);
            expect(condition.id).toBe(0);
            expect(condition.get('choice')).toBe(null);
            expect(condition.get('operator')).toBe(null);
            expect(condition.get('value')).toBe('abc123');
            expect(condition.get('valid')).toBe(false);
            expect(condition.get('error')).toBe('My error');

            expect(conditionSet.get('lastID')).toBe(0);
        });
    });

    describe('Adding to conditions collection', function() {
        let conditionSet;

        beforeEach(function() {
            conditionSet = new Djblets.Forms.ConditionSet({
                choicesData: [{
                    id: 'my-choice',
                    name: 'My Choice',
                    operators: [
                        {
                            id: 'my-op',
                            name: 'My Op'
                        }
                    ]
                }]
            });

            expect(conditionSet.get('lastID')).toBe(null);
        });

        it('Using choice and operator IDs', function() {
            conditionSet.conditions.add({
                choiceID: 'my-choice',
                operatorID: 'my-op',
                value: 'abc123',
                valid: false,
                error: 'My error'
            });

            const conditions = conditionSet.conditions;
            expect(conditions.length).toBe(1);

            const condition = conditions.at(0);
            expect(condition.id).toBe(0);
            expect(condition.get('choice').id).toBe('my-choice');
            expect(condition.get('operator').id).toBe('my-op');
            expect(condition.get('value')).toBe('abc123');
            expect(condition.get('valid')).toBe(false);
            expect(condition.get('error')).toBe('My error');

            expect(conditionSet.get('lastID')).toBe(0);
        });

        it('Using choice instance', function() {
            conditionSet.conditions.add({
                choiceID: conditionSet.choices.at(0),
                operatorID: 'my-op',
                value: 'abc123',
                valid: false,
                error: 'My error'
            });

            const conditions = conditionSet.conditions;
            expect(conditions.length).toBe(1);

            const condition = conditions.at(0);
            expect(condition.id).toBe(0);
            expect(condition.get('choice').id).toBe('my-choice');
            expect(condition.get('operator').id).toBe('my-op');
            expect(condition.get('value')).toBe('abc123');
            expect(condition.get('valid')).toBe(false);
            expect(condition.get('error')).toBe('My error');

            expect(conditionSet.get('lastID')).toBe(0);
        });

        it('Using operator instance', function() {
            conditionSet.conditions.add({
                choiceID: 'my-choice',
                operatorID: conditionSet.choices.at(0).operators.at(0),
                value: 'abc123',
                valid: false,
                error: 'My error'
            });

            const conditions = conditionSet.conditions;
            expect(conditions.length).toBe(1);

            const condition = conditions.at(0);
            expect(condition.id).toBe(0);
            expect(condition.get('choice').id).toBe('my-choice');
            expect(condition.get('operator').id).toBe('my-op');
            expect(condition.get('value')).toBe('abc123');
            expect(condition.get('valid')).toBe(false);
            expect(condition.get('error')).toBe('My error');

            expect(conditionSet.get('lastID')).toBe(0);
        });
    });

    describe('Methods', function() {
        it('addNewCondition', function() {
            const conditionSet = new Djblets.Forms.ConditionSet({
                fieldName: 'my-conditions',
                choicesData: [{
                    id: 'my-choice',
                    name: 'My Choice',
                    operators: [{
                        id: 'my-op',
                        name: 'My Op'
                    }]
                }]
            });

            const conditions = conditionSet.conditions;

            expect(conditions.length).toBe(0);
            expect(conditionSet.get('lastID')).toBe(null);

            conditionSet.addNewCondition();

            expect(conditions.length).toBe(1);
            expect(conditionSet.get('lastID')).toBe(0);

            const condition = conditions.at(0);
            expect(condition.id).toBe(0);
            expect(condition.get('choice').id).toBe('my-choice');
            expect(condition.get('operator').id).toBe('my-op');
        });
    });
});
