/**
 * A popup for selecting an integration to add.
 */

import {
    BaseView,
    spina,
} from '@beanbag/spina';
import * as _ from 'underscore';


/**
 * Data for an integration in the popup.
 *
 * Version Added:
 *     6.0
 */
export interface IntegrationOptions {
    /** The URL for adding the integration. */
    addURL: string;

    /** The description of the integration. */
    description: string;

    /** The value to use for the <img src> attribute. */
    iconSrc: string;

    /** The value to use for the <img srcset> attribute. */
    iconSrcSet: string;

    /** The internal ID of the integration. */
    id: string;

    /** The name of the integration. */
    name: string;
}


/**
 * Options for the AddIntegrationPopupView.
 *
 * Version Added:
 *     6.0
 */
export interface AddIntegrationPopupViewOptions {
    /** The list of integration types. */
    integrations: IntegrationOptions[];
}


/**
 * A popup for selecting an integration to add.
 */
@spina({
    prototypeAttrs: [
        'emptyIntegrationsTemplateSource',
        'integrationTemplateSource',
    ],
})
export class AddIntegrationPopupView extends BaseView<
    undefined,
    HTMLDivElement,
    AddIntegrationPopupViewOptions
> {
    static className = 'djblets-c-integrations-popup';

    /**
     * The pre-compiled template for an integration in the popup.
     *
     * This will be compiled when the popup is first being built, if
     * integrations are available.
     */
    static integrationTemplateSource = dedent`
        <li class="djblets-c-integration">
         <a href="<%- addURL %>">
          <% if (iconSrc) { %>
           <img class="djblets-c-integration__icon"
                src="<%- iconSrc %>"
                srcset="<%- iconSrcSet %>"
                width="48" height="48" alt="">
          <% } %>
          <div class="djblets-c-integration__details">
           <div class="djblets-c-integration__name"><%- name %></div>
           <div class="djblets-c-integration__description">
            <%- description %>
           </div>
          </div>
         </a>
        </li>
    `;
    declare integrationTemplateSource: string;

    /**
     * The pre-compiled template for the empty integrations popup content.
     *
     * This will be compiled when the popup is first being built, if
     * integrations are not available.
     */
    static emptyIntegrationsTemplateSource = dedent`
        <p class="djblets-c-integrations-popup__empty">
         ${_.escape(_`There are no integrations currently installed.`)}
        </p>
    `;
    declare emptyIntegrationsTemplateSource: string;

    /**********************
     * Instance variables *
     **********************/

    /** Data for the integrations items. */
    integrations: IntegrationOptions[];

    /**
     * Initialize the view.
     *
     * Args:
     *     options (AddIntegrationPopupViewOptions):
     *         Options passed to the view.
     */
    initialize(
        options: AddIntegrationPopupViewOptions,
    ) {
        this.integrations = options.integrations;
    }

    /**
     * Render the list of integrations in the popup.
     *
     * If there are integrations to display, the
     * :js:attr:`integrationTemplateSource` attribute will be used for each
     * item.
     *
     * If there aren't any integrations to display, the
     * :js:attr:`emptyIntegrationsTemplateSource` attribute will be used
     * for the contents.
     */
    protected onInitialRender() {
        const integrations = this.integrations;

        if (integrations.length > 0) {
            /* We have integrations to show. Add each to the list. */
            const itemTemplate = _.template(this.integrationTemplateSource);
            const $list = $('<ul>');

            for (let i = 0; i < integrations.length; i++) {
                $list.append(itemTemplate(integrations[i]));
            }

            this.$el.append($list);
        } else {
            /*
             * There are no integrations installed. Display an appropriate
             * message.
             */
            this.$el
                .addClass('-is-empty')
                .append(_.template(this.emptyIntegrationsTemplateSource)());
        }
    }

    /**
     * Remove the view.
     *
     * This will first hide the popup, unregistering any events, and will
     * then remove the element from the DOM.
     */
    protected onRemove() {
        this.hide();

        super.onRemove();
    }

    /**
     * Show the popup, anchored to a button.
     *
     * The popup will be displayed on the screen, presenting the list of
     * rendered integrations. The top-left of the popup will be anchored to
     * the bottom-left of the provided button.
     *
     * Events are hooked up to automatically dismiss the popup when clicking
     * away from the popup or resizing the window.
     *
     * Args:
     *     $button (jQuery):
     *         The button element to anchor to.
     */
    show(
        $button: JQuery,
    ) {
        const $window = $(window);
        const $el = this.$el;
        const el = this.el;
        const buttonPos = $button.position();

        /*
         * First, position the popup and set it to a small size to trigger
         * scrolling behavior, so we can perform calculations. It does need
         * to be big enough to fit the scrollbar, though, hence the width.
         */
        $el
            .move(buttonPos.left,
                  buttonPos.top + $button.outerHeight(),
                  'absolute')
            .width(100)
            .height(1)
            .show();

        const popupBorderWidths = $el.getExtents('b', 'lr');
        const scrollbarWidth = el.offsetWidth - el.clientWidth -
                               popupBorderWidths;

        const popupOffset = $el.offset();
        const popupHeight = Math.floor(
            $window.height() - popupOffset.top -
            $el.getExtents('bm', 'tb'));

        /*
         * Set the new width and height.
         *
         * We're resetting the height back to "auto" so it's not forced to be
         * too big, but cap around the screen boundary so it can't grow too
         * large.
         */
        $el.css({
            'height': 'auto',
            'max-height': popupHeight,
        });

        if ($el.hasClass('-is-empty')) {
            $el.css('width', 'auto');
        } else {
            /*
             * Get the width of one of the integration tiles in the popup, so
             * we can start to figure out how many we can fit on screen.
             */
            const tileWidth = $el
                .find('.djblets-c-integration')
                .filter(':first')
                .outerWidth(true);
            const winWidth = $window.width();
            const availWidth = winWidth - popupOffset.left - scrollbarWidth -
                               $el.getExtents('m', 'r');

            let popupWidth = Math.max(Math.floor(availWidth / tileWidth), 1) *
                             tileWidth + scrollbarWidth + popupBorderWidths;

            $el.outerWidth(popupWidth);

            /*
             * Now that we have a width and height set, we might not actually
             * be showing a scrollbar anymore. Find out how much extra space we
             * now have here, and if it's not what we had before for the scroll
             * bar, we can strip that out.
             */
            const newScrollbarWidth = el.offsetWidth -
                                      el.clientWidth -
                                      popupBorderWidths;

            if (newScrollbarWidth === 0) {
                popupWidth -= scrollbarWidth;
                $el.outerWidth(popupWidth);
            }

            /*
             * If the menu is off-screen (which might be due to a very small
             * screen width), we'll need to shift the popup over a bit.
             */
            if (popupOffset.left + popupWidth > winWidth) {
                $el.css('left', winWidth - popupWidth);
            }
        }

        /*
         * Wire up events to hide the popup when the document is clicked or
         * the window resized.
         */
        $(document).one('click.djblets-integrations-popup',
                        this.hide.bind(this));
        $(window).one('resize.djblets-integrations-popup',
                      this.hide.bind(this));
    }

    /**
     * Hide the popup.
     *
     * This will hide the popup from the screen and disconnect all related
     * events.
     */
    hide() {
        this.$el.hide();

        $(document).off('click.djblets-integrations-popup');
        $(window).off('resize.djblets-integrations-popup');
    }
}
