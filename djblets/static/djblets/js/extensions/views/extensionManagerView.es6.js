(function() {


/**
 * Displays an extension in the Manage Extensions list.
 *
 * This will show information about the extension, and provide links for
 * enabling/disabling the extension, and (depending on the extension's
 * capabilities) configuring it or viewing its database.
 */
const InstalledExtensionView = Backbone.View.extend({
    className: 'extension',
    tagName: 'li',

    events: {
        'click .enable-toggle': '_toggleEnableState',
        'click .reload-link': '_reloadExtensions',
    },

    template: _.template(dedent`
        <div class="extension-header">
         <h1><%- name %> <span class="version"><%- version %></span></h1>
         <p class="author">
          <% if (authorURL) { %>
           <a href="<%- authorURL %>"><%- author %></a>
          <% } else { %>
           <%- author %>
          <% } %>
         </p>
        </div>
        <div class="description"><%- summary %></div>
        <% if (!loadable) { %>
         <div class="extension-load-error">
          <p><%- loadFailureText %></p>
          <pre><%- loadError %></pre>
         </div>
        <% } %>
        <ul class="object-tools">
         <li><a href="#" class="enable-toggle"></a></li>
         <% if (loadError) { %>
          <li><a href="#" class="reload-link"><%- reloadText %></a></li>
         <% } else { %>
          <% if (configURL) { %>
           <li><a href="<%- configURL %>" class="enabled-only changelink">
               <%- configureText %></a></li>
          <% } %>
          <% if (dbURL) { %>
           <li><a href="<%- dbURL %>" class="enabled-only changelink">
               <%- databaseText %></a></li>
          <% } %>
         <% } %>
        </ul>
    `),

    /**
     * Render the extension in the list.
     *
     * Returns:
     *     InstalledExtensionView:
     *     This object, for chaining.
     */
    render() {
        this._renderTemplate();

        this.listenTo(this.model, 'change:loadable change:loadError',
                      this._renderTemplate);
        this.listenTo(this.model,
                      'change:enabled change:canEnable change:canDisable',
                      this._showEnabledState);

        return this;
    },

    /**
     * Render the template for the extension.
     *
     * This will render the template based on the current page conditions.
     * It's called when first rendering the extension and whenever there's
     * another need to do a full re-render (such as when loading an extension
     * fails).
     */
    _renderTemplate() {
        this.$el
            .html(this.template(_.defaults({
                configureText: gettext('Configure'),
                databaseText: gettext('Database'),
                loadFailureText: gettext('This extension failed to load with the following error:'),
                reloadText: gettext('Reload'),
            }, this.model.attributes)))
            .toggleClass('error', !this.model.get('loadable'));

        this._$enableToggle = this.$('.enable-toggle');
        this._$enabledToolLinks = this.$('.enabled-only');
        this._showEnabledState();
    },

    /**
     * Update the view to reflect the current enabled state.
     *
     * The Enable/Disable link will change to reflect the state, and
     * other links (Configure and Database) will be hidden if disabled.
     */
    _showEnabledState() {
        const enabled = this.model.get('enabled');

        this.$el
            .toggleClass('enabled', enabled)
            .toggleClass('disabled', !enabled);

        this._$enableToggle
            .text(enabled ? gettext('Disable') : gettext('Enable'))
            .toggleClass('enablelink', enabled)
            .toggleClass('disablelink', !enabled)
            .setVisible((enabled && this.model.get('canDisable')) ||
                        (!enabled && this.model.get('canEnable')));
        this._$enabledToolLinks.setVisible(enabled);
    },

    /**
     * Toggle the enabled state of the extension.
     *
     * Returns:
     *     boolean:
     *     false, always.
     */
    _toggleEnableState() {
        if (this.model.get('enabled')) {
            this.model.disable();
        } else {
            this.model.enable();
        }

        return false;
    },

    /**
     * Reload the extensions list.
     *
     * Returns:
     *     boolean:
     *     false, always.
     */
    _reloadExtensions() {
        this.trigger('reloadClicked');
        return false;
    },
});


/**
 * Displays the interface showing all installed extensions.
 *
 * This loads the list of installed extensions and displays each in a list.
 */
Djblets.ExtensionManagerView = Backbone.View.extend({
    events: {
        'click #reload-extensions': '_reloadFull',
    },

    /**
     * Initialize the view.
     */
    initialize() {
        this._$extensions = null;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     Djblets.ExtensionManagerView:
     *     This object, for chaining.
     */
    render() {
        this._$extensions = this.$('.extensions');

        this.listenTo(this.model, 'loaded', this._onLoaded);

        this.model.load();

        return this;
    },

    /**
     * Handler for when the list of extensions is loaded.
     *
     * Renders each extension in the list. If the list is empty, this will
     * display that there are no extensions installed.
     */
    _onLoaded() {
        this._$extensions.empty();

        if (this.model.installedExtensions.length === 0) {
            $('<li/>')
                .text(gettext('There are no extensions installed.'))
                .appendTo(this._$extensions);
        } else {
            let evenRow = false;

            this.model.installedExtensions.each(extension => {
                const view = new InstalledExtensionView({
                    model: extension,
                });

                this._$extensions.append(view.$el);
                view.$el.addClass(evenRow ? 'row2' : 'row1');
                view.render();

                this.listenTo(view, 'reloadClicked', this._reloadFull);

                evenRow = !evenRow;
            });

            this._$extensions.appendTo(this.$el);
        }
    },

    /**
     * Perform a full reload of the list of extensions on the server.
     *
     * This submits our form, which is set in the template to tell the
     * ExtensionManager to do a full reload.
     */
    _reloadFull: function() {
        this.el.submit();
    },
});


})();
