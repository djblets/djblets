PIPELINE_JAVASCRIPT = {
    'djblets-avatars-config': {
        'source_filenames': (
            'djblets/js/avatars/index.ts',
        ),
        'output_filename': 'djblets/js/avatars-config.min.js',
    },
    'djblets-config-forms': {
        'source_filenames': (
            'djblets/js/configForms/index.ts',
        ),
        'output_filename': 'djblets/js/config-forms.min.js',
    },
    'djblets-datagrid': {
        'source_filenames': (
            'djblets/js/datagrid/index.ts',

            # Legacy JavaScript
            'djblets/js/datagrid.js',
        ),
        'output_filename': 'djblets/js/datagrid.min.js',
    },
    'djblets-extensions-admin': {
        'source_filenames': (
            'djblets/js/extensionsAdmin/index.ts',
        ),
        'output_filename': 'djblets/js/extensions-admin.min.js',
    },
    'djblets-extensions': {
        'source_filenames': (
            'djblets/js/extensions/index.ts',
        ),
        'output_filename': 'djblets/js/extensions.min.js',
    },
    'djblets-forms': {
        'source_filenames': (
            'djblets/js/forms/index.ts',

            # Legacy JavaScript
            'djblets/js/forms/models/conditionChoiceModel.es6.js',
            'djblets/js/forms/models/conditionModel.es6.js',
            'djblets/js/forms/models/conditionOperatorModel.es6.js',
            'djblets/js/forms/models/conditionSetModel.es6.js',
            'djblets/js/forms/models/conditionValueField.es6.js',
            'djblets/js/forms/views/baseConditionValueFieldView.es6.js',
            'djblets/js/forms/views/conditionSetView.es6.js',
            'djblets/js/forms/views/conditionValueFormFieldView.es6.js',
            'djblets/js/forms/views/listEditView.es6.js',
            'djblets/js/forms/views/privacyConsentFieldView.es6.js',
        ),
        'output_filename': 'djblets/js/forms.min.js',
    },
    'djblets-integrations': {
        'source_filenames': (
            'djblets/js/integrations/index.ts',

            # Legacy JavaScript
            'djblets/js/integrations/views/addIntegrationPopupView.es6.js',
            'djblets/js/integrations/views/integrationConfigListView.es6.js',
        ),
        'output_filename': 'djblets/js/integrations.min.js',
    },
    'djblets-gravy': {
        'source_filenames': (
            # Legacy JavaScript
            #
            # These are in dependency order
            'djblets/js/jquery.gravy.util.js',
            'djblets/js/jquery.gravy.retina.js',
            'djblets/js/jquery.gravy.autosize.js',
            'djblets/js/jquery.gravy.inlineEditor.js',
            'djblets/js/jquery.gravy.modalBox.js',
            'djblets/js/jquery.gravy.tooltip.js',
            'djblets/js/jquery.gravy.funcQueue.js',
            'djblets/js/jquery.gravy.backboneUtils.js',
        ),
        'output_filename': 'djblets/js/jquery.gravy.min.js',
    },
    'djblets-js-tests': {
        'source_filenames': (
            'djblets/js/tests/index.ts',

            # Legacy JavaScript
            #
            # These are in dependency order
            'djblets/js/tests/backboneUtilsTests.js',
            'djblets/js/forms/models/tests/conditionChoiceModelTests.es6.js',
            'djblets/js/forms/models/tests/conditionModelTests.es6.js',
            'djblets/js/forms/models/tests/conditionOperatorModelTests.es6.js',
            'djblets/js/forms/models/tests/conditionSetModelTests.es6.js',
            'djblets/js/forms/views/tests/conditionSetViewTests.es6.js',
            'djblets/js/forms/views/tests/conditionValueFormFieldViewTests.es6.js',
            'djblets/js/forms/views/tests/listEditViewTests.es6.js',
            'djblets/js/integrations/views/tests/addIntegrationPopupViewTests.es6.js',
            'djblets/js/integrations/views/tests/integrationConfigListViewTests.es6.js',
            'djblets/js/utils/tests/urlsTests.es6.js',
        ),
        'output_filename': 'djblets/js/tests.min.js',
    },
    'djblets-utils': {
        'source_filenames': (
            'djblets/js/utils/index.ts',

            # Legacy JavaScript
            'djblets/js/utils/promise.es6.js',
        ),
        'output_filename': 'djblets/js/utils.min.js',
    },
    'djblets-widgets': {
        'source_filenames': (
            # Legacy JavaScript
            'djblets/js/admin/views/relatedObjectSelectorView.es6.js',
            'lib/js/selectize-0.12.4.js',
        ),
        'output_filename': 'djblets/js/widgets.min.js',
    },
}


PIPELINE_STYLESHEETS = {
    'djblets-avatars-config': {
        'source_filenames': (
            'djblets/css/avatars.less',
        ),
        'output_filename': 'djblets/css/avatars-config.min.css',
    },
    'djblets-admin': {
        'source_filenames': (
            'djblets/css/admin.less',
            'djblets/css/extensions.less',
        ),
        'output_filename': 'djblets/css/admin.min.css',
    },
    'djblets-forms': {
        'source_filenames': (
            'djblets/css/forms/conditions.less',
            'djblets/css/forms/copyable_text_input.less',
            'djblets/css/forms/list_edit.less',
            'djblets/css/forms/privacy.less',
        ),
        'output_filename': 'djblets/css/forms.min.css',
    },
    'djblets-config-forms': {
        'source_filenames': (
            'djblets/css/config-forms.less',
        ),
        'output_filename': 'djblets/css/config-forms.min.css',
    },
    'djblets-datagrid': {
        'source_filenames': (
            'djblets/css/datagrid.less',
        ),
        'output_filename': 'djblets/css/datagrid.min.css',
    },
    'djblets-integrations': {
        'source_filenames': (
            'djblets/css/integrations.less',
        ),
        'output_filename': 'djblets/css/integrations.min.css',
    },
    'djblets-ui': {
        'source_filenames': (
            'lib/css/selectize.default-0.12.4.css',
            'djblets/css/ui/modalbox.less',
            'djblets/css/ui/related-object-selector.less',
            'djblets/css/ui/spinner.less',
        ),
        'output_filename': 'djblets/css/ui.min.css',
        'absolute_paths': False,
    },
}
