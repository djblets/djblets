suite('djblets/utils/urls', function() {
    describe('parseQueryString', function() {
        it('Empty query string', function() {
            expect(Djblets.parseQueryString('')).toEqual({});
        });

        it('Basic query strings', function() {
            expect(Djblets.parseQueryString('?a=b&c=d&e=f')).toEqual({
                a: 'b',
                c: 'd',
                e: 'f',
            });
        });

        it('Keys without values', function() {
            expect(Djblets.parseQueryString('?abc=def&ghi')).toEqual({
                abc: 'def',
                ghi: null,
            });
        });

        describe('Multiple values for keys', function() {
            it('With allowMultiValue=true', function() {
                const queryString =
                    Djblets.parseQueryString('?a=1&a=2&a=3&b=4', {
                        allowMultiValue: true,
                    });

                expect(queryString).toEqual({
                    a: ['1', '2', '3'],
                    b: '4',
                });
            });

            it('Without allowMultiValue=true', function() {
                expect(Djblets.parseQueryString('?a=1&a=2&a=3&b=4')).toEqual({
                    a: '3',
                    b: '4',
                });
            });
        });
    });
});
