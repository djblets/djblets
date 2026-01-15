/**
 * View to manage a collection of configuration pages.
 */

import { BaseView, spina } from '@beanbag/spina';
import * as Backbone from 'backbone';


/**
 * View to manage a collection of configuration pages.
 *
 * The primary job of this view is to handle sub-page navigation.
 * The actual page will contain several "pages" that are shown or hidden
 * depending on what the user has clicked on the sidebar.
 */
@spina
export class PagesView<
    TModel extends Backbone.Model = undefined
> extends BaseView<TModel> {
    /**********************
     * Instance variables *
     **********************/

    /** The page router. */
    router: Backbone.Router;

    /**
     * All subpage navigation item elements.
     */
    _$pageNavs: JQuery;

    /**
     * All subpage elements on the page.
     */
    _$pages: JQuery;

    /** The active navigation item. */
    #$activeNav: JQuery;

    /** The active page. */
    #$activePage: JQuery;

    /** Whether to preserve the ``#messages`` element when switching pages. */
    #preserveMessages: boolean;

    /**
     * Initialize the view.
     *
     * This will set up the router for handling page navigation.
     */
    initialize() {
        this.router = new Backbone.Router({
            routes: {
                ':pageID': 'page',
            },
        });
        this.listenTo(this.router, 'route:page', this._onPageChanged);

        this.#$activeNav = null;
        this.#$activePage = null;
        this.#preserveMessages = true;
    }

    /**
     * Render the view.
     *
     * This will set the default page to be shown, and instruct Backbone
     * to begin handling the routing.
     */
    protected onInitialRender() {
        this._$pageNavs = this.$('.djblets-c-config-forms-page-nav__item');
        this._$pages = this.$('.djblets-c-config-forms-subpage');

        this.#$activeNav = this._$pageNavs.eq(0).addClass('-is-active');
        this.#$activePage = this._$pages.eq(0).addClass('-is-active');

        Backbone.history.start({
            root: window.location.pathname,
        });
    }

    /**
     * Handle when the page changes.
     *
     * The sidebar will be updated to reflect the current active page,
     * and the page will be shown.
     *
     * If navigating pages manually, any messages provided by the backend
     * form will be removed. We don't do this the first time there's a
     * navigation, as this will be called when first rendering the view.
     *
     * Args:
     *     pageID (string):
     *         The ID of the page that is becoming active.
     */
    _onPageChanged(pageID: string) {
        this.#$activeNav.removeClass('-is-active');
        this.#$activePage.removeClass('-is-active');

        this.#$activePage = $(`#page_${pageID}`);

        if (this.#$activePage.length === 0) {
            /*
             * If the requested page doesn't exist (for example, it might be
             * hidden, or just typoed), load the first page instead.
             */
            this.router.navigate(
                this._$pageNavs.find('a').attr('href').substr(1),
                {
                    replace: true,
                    trigger: true,
                });
        } else {
            this.#$activeNav =
                this._$pageNavs
                    .filter(`:has(a[href="#${pageID}"])`)
                    .addClass('-is-active');

            this.#$activePage.addClass('-is-active');

            if (!this.#preserveMessages) {
                $('#messages').remove();
            }

            this.#preserveMessages = false;
        }
    }
}
