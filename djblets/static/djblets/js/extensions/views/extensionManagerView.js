var InstalledExtensionView;


/*
 * Displays an extension in the Manage Extensions list.
 *
 * This will show information about the extension, and provide links for
 * enabling/disabling the extension, and (depending on the extension's
 * capabilities) configuring it or viewing its database.
 */
InstalledExtensionView = Backbone.View.extend({
    className: 'extension',
    tagName: 'li',

    events: {
        'click .enable-toggle': '_toggleEnableState'
    },

    template: _.template([
        '<div class="extension-header">',
        ' <h1><%- name %> <span class="version"><%- version %></span></h1>',
        ' <p class="author">',
        '  <% if (authorURL) { %>',
        '   <a href="<%- authorURL %>"><%- author %></a>',
        '  <% } else { %>',
        '   <%- author %>',
        '  <% } %>',
        ' </p>',
        '</div>',
        '<div class="description"><%- summary %></div>',
        '<ul class="object-tools">',
        ' <li><a href="#" class="enable-toggle"></a></li>',
        ' <% if (configURL) { %>',
        '  <li><a href="<%- configURL %>" class="enabled-only changelink">',
        '      Configure</a></li>',
        ' <% } %>',
        ' <% if (dbURL) { %>',
        '  <li><a href="<%- dbURL %>" class="enabled-only changelink">',
        '      Database</a></li>',
        ' <% } %>',
        '</ul>',
    ].join('')),

    /*
     * Renders the extension in the list.
     */
    render: function() {
        this.$el.html(this.template(this.model.attributes));

        this._$enableToggle = this.$('.enable-toggle');
        this._$enabledToolLinks = this.$('.enabled-only');

        this.listenTo(this.model, 'change:enabled', this._showEnabledState);
        this._showEnabledState();

        return this;
    },

    /*
     * Updates the view to reflect the current enabled state.
     *
     * The Enable/Disable link will change to reflect the state, and
     * other links (Configure and Database) will be hidden if disabled.
     */
    _showEnabledState: function() {
        var enabled = this.model.get('enabled');

        this._$enableToggle
            .text(enabled ? 'Disable' : 'Enable')
            .addClass(enabled ? 'disablelink' : 'enablelink')
            .removeClass(enabled ? 'enablelink' : 'disablelink');
        this._$enabledToolLinks.setVisible(enabled);
    },

    /*
     * Toggles the enabled state of the extension.
     */
    _toggleEnableState: function() {
        if (this.model.get('enabled')) {
            this.model.disable();
        } else {
            this.model.enable();
        }

        return false;
    }
});


/*
 * A collection of installed extensions.
 *
 * This stores the list of installed extensions, and allows fetching from
 * the API.
 */
InstalledExtensionCollection = Backbone.Collection.extend({
    model: InstalledExtension,

    url: function() {
        return SITE_ROOT + 'api/extensions/';
    },

    parse: function(rsp) {
        return rsp.extensions;
    }
});


/*
 * Displays the interface showing all installed extensions.
 *
 * This loads the list of installed extensions and displays each in a list.
 */
Djblets.ExtensionManagerView = Backbone.View.extend({
    initialize: function() {
        this._$extensions = null;
    },

    render: function() {
        this._$extensions = this.$('.extensions');

        this.listenTo(this.model, 'loaded', this._onLoaded);

        this.model.load();

        return this;
    },

    /*
     * Handler for when the list of extensions is loaded.
     *
     * Renders each extension in the list. If the list is empty, this will
     * display that there are no extensions installed.
     */
    _onLoaded: function() {
        var evenRow = false;

        this._$extensions.empty();

        if (this.model.installedExtensions.length === 0) {
            this._$extensions.append(
                $('<li/>').text('There are no extensions installed.'));
        } else {
            this.model.installedExtensions.each(function(extension) {
                var view = new InstalledExtensionView({
                    model: extension
                });

                this._$extensions.append(view.$el);
                view.$el.addClass(evenRow ? 'row2' : 'row1');
                view.render();

                evenRow = !evenRow;
            }, this);

            this._$extensions.appendTo(this.$el);
        }
    }
});
