(function() {


const allowedMimeTypes = [
    'image/png', 'image/jpeg', 'image/gif'
];


/**
 * A file upload avatar settings form.
 *
 * This form provides a preview of the uploaded avatar.
 */
Djblets.Avatars.FileUploadSettingsFormView = Djblets.Avatars.ServiceSettingsFormView.extend({
    events: {
        'change #id_file-upload-avatar_upload': '_onFileChanged'
    },


    /**
     * Validate the form.
     *
     * If a file is selected, ensure it is has the correct MIME type.
     */
    validate() {
        const file = this.$('#id_file-upload-avatar_upload')[0].files[0];

        if (!file) {
            alert(gettext('You must choose a file.'));
            return false;
        }

        if (!allowedMimeTypes.some(el => el === file.type)) {
            alert(gettext('Invalid file format'));
            return false;
        }

        return true;
    },

    /**
     * Render the form.
     *
     * Returns:
     *     Djblets.Avatars.FileUploadSettingsFormView:
     *     This view (for chaining).
     */
    render() {
        this._$preview = this.$('.avatar-preview');

        return this;
    },

    /**
     * Handle to the selected file being changed.
     *
     * This will update the preview image.
     *
     * Args:
     *     e (Event):
     *         The change event.
     */
    _onFileChanged(e) {
        const file = e.target.files[0];

        if (file) {
            const reader = new FileReader();
            reader.addEventListener('load', () => {
                this._$preview
                    .children()
                    .eq(0)
                    .replaceWith(
                        $('<img />')
                            .attr('src', reader.result)
                    );
            });

            reader.readAsDataURL(file);
        }
    }
});


})();
