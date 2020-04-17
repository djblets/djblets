(function() {


const allowedMimeTypes = [
    'image/png', 'image/jpeg', 'image/gif'
];


const ParentView = Djblets.Avatars.ServiceSettingsFormView;


/**
 * A file upload avatar settings form.
 *
 * This form provides a preview of the uploaded avatar.
 */
Djblets.Avatars.FileUploadSettingsFormView = ParentView.extend({
    events: {
        'change #id_file-upload-avatar_upload': '_onFileChanged',
        'click .avatar-file-upload-browse': '_onBrowseClicked',
        'click .avatar-preview': '_onBrowseClicked',
        'dragenter .avatar-file-upload-config': '_onDragEnter',
        'dragover .avatar-file-upload-config': '_onDragOver',
        'dragleave .avatar-file-upload-config': '_onDragLeave',
        'drop .avatar-file-upload-config': '_onDrop',
    },

    /**
     * Validate the form.
     *
     * If a file is selected, ensure it is has the correct MIME type.
     */
    validate() {
        const file = this._$fileInput[0].files[0];

        if (!file) {
            alert(_`You must choose a file.`);
            return false;
        }

        if (!allowedMimeTypes.some(el => (el === file.type))) {
            alert(_`
                This wasn't a valid image file format. Please provide a PNG,
                JPEG, or GIF file.
            `);
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
        this._$box = this.$('.avatar-file-upload-config');
        this._$preview = this.$('.avatar-preview');
        this._$fileInput = this.$('#id_file-upload-avatar_upload');

        return this;
    },

    /**
     * Handler for a click event on the "browse" instruction text.
     *
     * This will trigger opening the hidden file input.
     *
     * Args:
     *     e (jQuery.Event):
     *         The click event.
     */
    _onBrowseClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        /*
         * Clicking on the file input itself is not reliable. There are ways
         * to make it work, but the browser actively avoids letting you do it if
         * it seems to be hidden. However, it works just fine universally to
         * click on the label.
         */
        this.$('#avatar-file-upload-browse-label').click();
    },

    /**
     * Handler for a drag enter event.
     *
     * If the configuration box is being hovered over, this will enable the
     * hover state, giving users an indication that they can drop the image
     * there.
     *
     * Args:
     *     e (jQuery.Event):
     *         The drag over event.
     */
    _onDragEnter(e) {
        e.preventDefault();
        e.stopPropagation();

        if (e.target === this._$box[0]) {
            this._$box
                .width(this._$box.width())
                .addClass('drag-hover');
        }
    },

    /**
     * Handler for a drag over event.
     *
     * If the configuration box is being hovered over, this will set the drop
     * effect.
     *
     * Args:
     *     e (jQuery.Event):
     *         The drag over event.
     */
    _onDragOver(e) {
        e.preventDefault();
        e.stopPropagation();

        if (e.target === this._$box[0]) {
            const dt = e.originalEvent.dataTransfer;

            if (dt) {
                dt.dropEffect = 'copy';
            }
        }
    },

    /**
     * Handler for a drag leave event.
     *
     * If the configuration box is being left, this will remove the hover state
     * and reset the drop effect.
     *
     * Args:
     *     e (jQuery.Event):
     *         The drag leave event.
     */
    _onDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();

        if (e.target === this._$box[0]) {
            this._$box
                .removeClass('drag-hover')
                .width('auto');

            const dt = e.originalEvent.dataTransfer;

            if (dt) {
                dt.dropEffect = 'none';
            }
        }
    },

    /**
     * Handler for a drop operation.
     *
     * This will remove the hover state and attempt to set the list of files
     * on the file input. If this fails (which will be the case on some browsers
     * with older behavior), the user will receive an alert telling them it
     * failed and to try browsing instead.
     *
     * If all goes well, the avatar will be ready for upload and the preview
     * image will be updated.
     *
     * Args:
     *     e (jQuery.Event):
     *         The drop event.
     */
    _onDrop(e) {
        e.preventDefault();
        e.stopPropagation();

        this._$box.removeClass('drag-hover');

        const dt = e.originalEvent.dataTransfer;
        const files = dt && dt.files;

        if (!files || files.length === 0) {
            return;
        }

        if (files.length > 1) {
            alert(_`
                You can only set one file as your avatar. Please drag and
                drop a single file.
            `);
            return;
        }

        const fileType = files[0].type;

        if (fileType !== 'image/png' && fileType !== 'image/jpeg' &&
            fileType !== 'image/gif') {
            alert(_`
                This doesn't appear to be a compatible image file for avatars.
                Please upload a PNG, JPEG, or GIF file.
            `);
            return;
        }

        try {
            this._$fileInput[0].files = files;
        } catch (exc) {
            /*
             * While most modern browsers allow setting the `files` property of
             * an input field to the rest of a drag-and-drop operation, not all
             * do (I'm looking at you, IE/Edge). Older browsers will also
             * complain. So instead of outright failing, tell the user that this
             * won't work and suggest a workaround.
             */
            alert(_`
                Looks like dragging to upload a file isn't going to work with
                your browser. Try browsing for a file instead.
            `);
            return;
        }

        this._setAvatarFromFile(files[0]);
    },

    /**
     * Handler for when the file input has changed.
     *
     * This will update the preview image.
     *
     * Args:
     *     e (jQuery.Event):
     *         The change event.
     */
    _onFileChanged(e) {
        const file = e.target.files[0];

        if (file) {
            this._setAvatarFromFile(file);
        }
    },

    /**
     * Set the avatar from the provided file upload.
     *
     * Args:
     *     file (File):
     *         The file that was uploaded.
     */
    _setAvatarFromFile(file) {
        const reader = new FileReader();

        reader.addEventListener('load', () => {
            this._$preview
                .empty()
                .removeClass('avatar-preview-unset')
                .append($('<img />').attr({
                     src: reader.result,
                     alt: _`Your new avatar`,
                 }));
        });

        reader.readAsDataURL(file);
    },
});


})();
