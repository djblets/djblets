suite('djblets/utils/urls', function() {
    describe('buildURL', function() {
        it('With just baseURL', function() {
            const url = Djblets.buildURL({
                baseURL: 'https://example.com/abc123/',
            });

            expect(url).toBe('https://example.com/abc123/');
        });

        describe('With anchor', function() {
            it('With leading "#"', function() {
                const url = Djblets.buildURL({
                    baseURL: 'https://example.com/abc123/',
                    anchor: '#my-anchor',
                });

                expect(url).toBe('https://example.com/abc123/#my-anchor');
            });

            it('Without leading "#"', function() {
                const url = Djblets.buildURL({
                    baseURL: 'https://example.com/abc123/',
                    anchor: 'my-anchor',
                });

                expect(url).toBe('https://example.com/abc123/#my-anchor');
            });
        });

        describe('With queryData', function() {
            describe('As string', function() {
                it('With leading "?"', function() {
                    const url = Djblets.buildURL({
                        baseURL: 'https://example.com/abc123/',
                        queryData: '?a=b&c=d',
                    });

                    expect(url).toBe('https://example.com/abc123/?a=b&c=d');
                });

                it('Without leading "?"', function() {
                    const url = Djblets.buildURL({
                        baseURL: 'https://example.com/abc123/',
                        queryData: 'a=b&c=d',
                    });

                    expect(url).toBe('https://example.com/abc123/?a=b&c=d');
                });

                it('Empty', function() {
                    const url = Djblets.buildURL({
                        baseURL: 'https://example.com/abc123/',
                        queryData: '',
                    });

                    expect(url).toBe('https://example.com/abc123/');
                });
            });

            describe('As object', function() {
                it('With value', function() {
                    const url = Djblets.buildURL({
                        baseURL: 'https://example.com/abc123/',
                        queryData: {
                            a: 'b',
                        },
                    });

                    expect(url).toBe('https://example.com/abc123/?a=b');
                });

                it('Empty', function() {
                    const url = Djblets.buildURL({
                        baseURL: 'https://example.com/abc123/',
                        queryData: {},
                    });

                    expect(url).toBe('https://example.com/abc123/');
                });
            });

            describe('As array', function() {
                it('With value', function() {
                    const url = Djblets.buildURL({
                        baseURL: 'https://example.com/abc123/',
                        queryData: [
                            {
                                name: 'a',
                                value: 'b',
                            },
                            {
                                name: 'c',
                                value: 'd',
                            },
                        ],
                    });

                    expect(url).toBe('https://example.com/abc123/?a=b&c=d');
                });

                it('Empty', function() {
                    const url = Djblets.buildURL({
                        baseURL: 'https://example.com/abc123/',
                        queryData: [],
                    });

                    expect(url).toBe('https://example.com/abc123/');
                });
            });
        });

        it('With all options', function() {
            const url = Djblets.buildURL({
                baseURL: 'https://example.com/abc123/',
                queryData: 'a=b&c=d',
                anchor: 'my-anchor',
            });

            expect(url).toBe(
                'https://example.com/abc123/?a=b&c=d#my-anchor');
        });
    });

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
