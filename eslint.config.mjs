/**
 * ESLint configuration.
 *
 * Version Added:
 *     5.3
 */

import beanbag from '@beanbag/eslint-plugin';
import {
    defineConfig,
    globalIgnores,
} from 'eslint/config';
import globals from 'globals';


export default defineConfig([
    globalIgnores([
        'djblets/htdocs/**/*',
        'djblets/static/lib/js/**',
    ]),
    beanbag.configs.recommended,
    {
        languageOptions: {
            ecmaVersion: 'latest',
            globals: {
                ...beanbag.globals.backbone,
                ...beanbag.globals.django,
                ...globals.browser,
                ...globals.jquery,
                Djblets: 'writable',
                dedent: 'readonly',
            },
        },
        plugins: {
            '@beanbag': beanbag,
        },
    },
]);
