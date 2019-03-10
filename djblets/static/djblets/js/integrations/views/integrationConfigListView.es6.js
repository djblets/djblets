/**
 * View for managing the integration configurations list.
 *
 * This handles events for the Add Integration button and the resulting popup.
 */
Djblets.IntegrationConfigListView = Backbone.View.extend({
    events: {
        'click .djblets-c-integration-configs__add': '_onAddIntegrationClicked',
    },

    /**
     * Render the view.
     *
     * Returns:
     *     Djblets.IntegrationConfigListView:
     *     This view, for chaining.
     */
    render() {
        this._$popup = this.$('.djblets-c-integrations-popup');

        return this;
    },

    /**
     * Hide the integrations list popup.
     *
     * This will hide the popup from the screen and disconnect all related
     * events.
     */
    _hidePopup() {
        this._$popup.hide();

        $(document).off('click.djblets-integrations-popup');
        $(window).off('resize.djblets-integrations-popup');
    },

    /**
     * Handler for the Add Integration button.
     *
     * This will show the integrations list popup, allowing the user to choose
     * an integration to add.
     *
     * The logic for showing the popup will align the popup with the left-hand
     * side of the Add Integration button, and set the width to the maximum
     * amount that will cleanly fit a row of tiles without obscuring any part
     * of a tile or leaving extra space after a tile.
     *
     * Args:
     *     e (jQuery.Event):
     *         The click event.
     */
    _onAddIntegrationClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        const $window = $(window);
        const $popup = this._$popup;
        const popupEl = $popup[0];
        const $button = $(e.target);
        const buttonPos = $button.position();

        /*
         * First, position the popup and set it to a small size to trigger
         * scrolling behavior, so we can perform calculations. It does need
         * to be big enough to fit the scrollbar, though, hence the width.
         */
        $popup
            .move(buttonPos.left,
                  buttonPos.top + $button.outerHeight(),
                  'absolute')
            .width(100)
            .height(1)
            .show();

        const popupBorderWidths = $popup.getExtents('b', 'lr');
        const scrollbarWidth = popupEl.offsetWidth - popupEl.clientWidth -
                               popupBorderWidths;

        const popupOffset = $popup.offset();
        const popupHeight = Math.floor(
            $window.height() - popupOffset.top -
            $popup.getExtents('bm', 'tb'));

        /*
         * Set the new width and height.
         *
         * We're resetting the height back to "auto" so it's not forced to be
         * too big, but cap around the screen boundary so it can't grow too
         * large.
         */
        $popup.css({
            'height': 'auto',
            'max-height': popupHeight,
        });

        if ($popup.hasClass('-is-empty')) {
            $popup.css('width', 'auto');
        } else {
            /*
             * Get the width of one of the integration tiles in the popup, so
             * we can start to figure out how many we can fit on screen.
             */
            const tileWidth = $popup
                .find('.djblets-c-integration')
                .filter(':first')
                .outerWidth(true);
            const winWidth = $window.width();
            const availWidth = winWidth - popupOffset.left - scrollbarWidth -
                               $popup.getExtents('m', 'r');

            let popupWidth = Math.max(Math.floor(availWidth / tileWidth), 1) *
                             tileWidth + scrollbarWidth + popupBorderWidths;

            $popup.outerWidth(popupWidth);

            /*
             * Now that we have a width and height set, we might not actually
             * be showing a scrollbar anymore. Find out how much extra space we
             * now have here, and if it's not what we had before for the scroll
             * bar, we can strip that out.
             */
            const newScrollbarWidth = popupEl.offsetWidth -
                                      popupEl.clientWidth -
                                      popupBorderWidths;

            if (newScrollbarWidth === 0) {
                popupWidth -= scrollbarWidth;
                $popup.outerWidth(popupWidth);
            }

            /*
             * If the menu is off-screen (which might be due to a very small
             * screen width), we'll need to shift the popup over a bit.
             */
            if (popupOffset.left + popupWidth > winWidth) {
                $popup.css('left', winWidth - popupWidth);
            }
        }

        /*
         * Wire up events to hide the popup when the document is clicked or
         * the window resized.
         */
        $(document).one('click.djblets-integrations-popup',
                        () => this._hidePopup());
        $(window).one('resize.djblets-integrations-popup',
                      () => this._hidePopup());
    },
});
