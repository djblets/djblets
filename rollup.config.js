import babel from '@rollup/plugin-babel';
import externalGlobals from 'rollup-plugin-external-globals';
import resolve from '@rollup/plugin-node-resolve';


const extensions = [
    '.es6.js',
    '.js',
    '.ts',
];


const globalsMap = {
    '@beanbag/spina': 'Spina',
    backbone: 'Backbone',
    django: 'django',
    djblets: 'Djblets',
    'jasmine-core': 'window',
    jquery: '$',
    underscore: '_',
};


export default {
    output: {
        /*
         * Anything exported from a top-level index.* file (as specified in
         * the Pipeline bundle configuration) will be placed in this top-level
         * variable.
         */
        name: 'Djblets',

        esModule: false,
        exports: 'named',
        extend: true,
        format: 'umd',
        sourcemap: true,

        /*
         * Each of these globals will be assumed to exist when the module is
         * loaded. They won't have to be imported.
         */
        globals: globalsMap,
    },
    plugins: [
        /* Configure rollup to use Babel to compile files. */
        babel({
            babelHelpers: 'bundled',
            extensions: extensions,
        }),

        /*
         * Convert any `djblets/*` module import paths to instead look up
         * in the `Djblets` top-level namespace variable.
         */
        externalGlobals(id => {
            if (id.startsWith('djblets/')) {
                return 'Djblets';
            }

            return globalsMap[id];
        }),

        /* Specify where modules should be looked up from. */
        resolve({
            extensions: extensions,
            modulePaths: [
                'djblets/static/lib/js',
                'djblets/static/djblets/js',
                'node_modules',
            ],
        }),
    ],
    treeshake: {
        /*
         * Make sure that any imported but unused modules are retained, not
         * ignored, as it's possible to import from a module and compile
         * before writing code to export anything in that module.
         *
         * In that particular case, if the imported module were ignored, the
         * Rollup compiler for Pipeline wouldn't know about it and wouldn't
         * check to see if a recompile is needed.
         *
         * This should be the default, but we want to be explicit here.
         */
        moduleSideEffects: true,
    },
};
