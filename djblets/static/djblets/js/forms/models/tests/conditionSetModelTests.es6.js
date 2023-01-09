suite('djblets/forms/models/ConditionSet', function() {
    describe('Initialization', function() {
        it('choicesData parsed', function() {
            const conditionSet = new Djblets.Forms.ConditionSet({
                choicesData: [{
                    id: 'my-choice',
                    name: 'My Choice',
                }],
                fieldName: 'my-conditions',
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
                            name: 'My Op 1',
                        },
                        {
                            id: 'my-op-2',
                            name: 'My Op 2',
                        },
                    ],
                }],
                conditionsData: [
                    {
                        choiceID: 'my-choice',
                        error: 'My error',
                        operatorID: 'my-op-1',
                        valid: false,
                        value: 'abc123',
                    },
                    {
                        choiceID: 'my-choice',
                        operatorID: 'my-op-2',
                        valid: true,
                        value: 42,
                    },
                ],
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
                            name: 'My Op 1',
                        },
                        {
                            id: 'my-op-2',
                            name: 'My Op 2',
                        },
                    ],
                }],
                conditionsData: [
                    {
                        choiceID: 'invalid-choice',
                        error: 'My error',
                        operatorID: 'my-op-1',
                        valid: false,
                        value: 'abc123',
                    },
                ],
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
                            name: 'My Op',
                        },
                    ],
                }],
            });

            expect(conditionSet.get('lastID')).toBe(null);
        });

        it('Using choice and operator IDs', function() {
            conditionSet.conditions.add({
                choiceID: 'my-choice',
                error: 'My error',
                operatorID: 'my-op',
                valid: false,
                value: 'abc123',
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
                error: 'My error',
                operatorID: 'my-op',
                valid: false,
                value: 'abc123',
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
                error: 'My error',
                operatorID: conditionSet.choices.at(0).operators.at(0),
                valid: false,
                value: 'abc123',
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
                choicesData: [{
                    id: 'my-choice',
                    name: 'My Choice',
                    operators: [{
                        id: 'my-op',
                        name: 'My Op',
                    }],
                }],
                fieldName: 'my-conditions',
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
