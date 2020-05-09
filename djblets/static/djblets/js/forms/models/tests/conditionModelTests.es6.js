suite('djblets/forms/models/Condition', () => {
    describe('Events', () => {
        describe('choice changes', () => {
            let choice1,
                choice2,
                condition;

            beforeEach(() => {
                choice1 = new Djblets.Forms.ConditionChoice({
                    id: 'my-choice-1',
                    name: 'My Choice 1',
                });
                choice1.operators.add({
                    id: 'my-op-1',
                    name: 'My Op 1'
                });

                choice2 = new Djblets.Forms.ConditionChoice({
                    id: 'my-choice-1',
                    name: 'My Choice 1',
                });
                choice2.operators.add([
                    {
                        id: 'my-op-2',
                        name: 'My Op 2'
                    },
                    {
                        id: 'my-op-3',
                        name: 'My Op 3'
                    }
                ]);

                condition = new Djblets.Forms.Condition({
                    choice: choice1,
                    operator: choice1.operators.first(),
                    value: 'abc123'
                });

                /* Now change the choice. */
                condition.set('choice', choice2);
            });

            it('Operator resets to first', () => {
                expect(condition.get('operator')).toBe(
                    choice2.operators.first());
            });

            it('Value resets', () => {
                expect(condition.get('value')).toBe(undefined);
            });
        });
    });
});
