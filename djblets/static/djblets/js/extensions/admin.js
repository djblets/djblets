function send_extension_webapi_request(extension_id, data) {
    $('#activity-indicator').show();
    $.ajax({
        type: "PUT",
        url: SITE_ROOT + "api/extensions/" + extension_id + "/",
        data: data,
        success: function(xhr) {
            window.location = window.location;
        },
        complete: function(xhr) {
            $('#activity-indicator').hide();
        },
        error: function(xhr) {
            /*
             * If something goes wrong, try to dump out the error
             * to a modal dialog.
             */
            var jsonData = eval("(" + xhr.responseText + ")");
            var dlg = $("<p/>")
            .text(jsonData['err']['msg'])
            .modalBox({
                title: "Error",
                buttons: [
                    $('<input type="button" value="OK"/>'),
                ]
            });
        }
    });
}


$(document).ready(function() {
    $('<div id="activity-indicator" />')
        .text("Loading...")
        .hide()
        .appendTo("body");
});
