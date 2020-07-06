#!/usr/bin/env node

/**
 * Extract a list of import dependencies from a top-level .less file.
 *
 * This is used to determine whether or not any given .less file needs to be
 * recompiled during development. The pipeline compiler in
 * djblets.pipeline.compilers.less will run this script to extract a deep list
 * of imports from a given file, which are then used to check the timestamps to
 * see if any of the dependencies are newer than the target file.
 *
 * On success, this will print out the file paths to any import dependencies,
 * one file per line, and exit with a return code of 0. On error, an error will
 * be written to stderr and the process will exit with a non-zero return code.
 */

var fs = require('fs'),
    less = require('less'),
    path = require('path');

/**
 * Parse arguments.
 *
 * This will parse ``process.argv`` similar to how the lessc command does. In
 * this case, we want to recognize the arguments that could be passed to lessc
 * but we don't actually care about most of them since the only things that
 * matter are those that affect import paths.
 *
 * Returns:
 *     object:
 *     An object with ``options`` and ``paths`` keys, containing the LessCSS
 *     options (which should be passed into :js:func:`less.parse`) and the file
 *     path of the .less file to scan.
 */
function parseArgs() {
    var args = process.argv.slice(2),
        options = {
            color: false,
            compless: false,
            depends: false,
            globalVars: null,
            ieCompat: true,
            insecure: false,
            lint: false,
            max_line_len: -1,
            modifyVars: null,
            paths: [],
            plugins: [],
            relativeUrls: false,
            rootpath: '',
            strictImports: false,
            strictMath: false,
            strictUnits: false,
            urlArgs: ''
        },
        paths;

    function checkArgFunc(arg, option) {
        if (!option) {
            console.error(arg + ' option requires a parameter');
            process.exit(1);
        }
    }

    function parseVariableOption(option, variables) {
        var parts = option.split('=', 2);
        variables[parts[0]] = parts[1];
    }

    paths = args.filter(function(arg) {
        var match = arg.match(/^--?([a-z][0-9a-z-]*)(?:=(.*))?$/i);

        if (match) {
            arg = match[1];
        } else {
            return arg;
        }

        switch(arg) {
            case 'global-var':
                checkArgFunc(arg, match[2]);
                if (!options.globalVars) {
                    options.globalVars = {};
                }
                parseVariableOption(match[2], options.globalVars);
                break;

            case 'include-path':
                checkArgFunc(arg, match[2]);
                options.paths = match[2]
                    .split(':')
                    .map(function(p) {
                        return path.resolve(process.cwd(), p);
                    });
                break;

            case 'no-color':
            case 'source-map':
            case 'autoprefix':
            case 'js':
            case 'rewrite-urls':
                // These don't matter for the imports check. No-op.
                break;

            default:
                console.error('less-imports.js: Un-handled argument "%s"', arg);
                process.exit(1);
        }
    });

    return {
        options: options,
        paths: paths
    };
}

var opts = parseArgs();
if (opts.paths.length !== 1) {
    console.error('Requires a single path argument');
    process.exit(1);
}

var path = opts.paths[0];
opts.options.filename = path;

fs.readFile(path, function(err, data) {
    if (err) {
        console.error('Could not read file "%s": %s', path, err);
        process.exit(1);
    }

    less.parse(data.toString('utf8'), opts.options, function(err, tree, imports) {
        var files, i;

        if (err) {
            console.error('Could not parse file "%s": %s', path, err);
            process.exit(1);
        }

        /*
         * LessCSS 3.11.3 uses an array for the list of files. Prior versions
         *
         * LessCSS 3.11.1 and older use an object.
         *
         * LessCSS 3.11.2 does not have a list of files at all. This might
         * come up again in the future, so explicitly check for this.
         */
        if (imports.files === undefined) {
            console.error('Unsupported version of LessCSS. The list of file ' +
                          'imports does not exist.');
            process.exit(1);
        }

        files = (Array.isArray(imports.files)
                 ? imports.files
                 : Object.keys(imports.files));

        for (i = 0; i < files.length; i++) {
            console.log(files[i]);
        }

        process.exit(0);
    });
});
