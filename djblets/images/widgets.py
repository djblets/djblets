from django.newforms.widgets import Widget
from django.utils.html import escape

class ImageWidget(Widget):
    def render(self, name, value, attrs=None):
        """Images render to two HTML elements: an iframe, which runs our
           asynchronous image uploader, and a hidden element which displays
           the result. Each time the iframe reloads, code in iframe.js will
           update the hidden element. Client-side code is also responsible
           for sizing the uploader dynamically.
           """
        try:
            value = int(value)
        except (ValueError, TypeError):
            value = ''
        
        return """
<iframe src="/images/upload?image-id=%(value)s"
        name="%(name)s_iframe"
        width="100%%" height="0px"
        frameborder="0" scrolling="no" marginheight="0" marginwidth="0"
        > </iframe>
<input name="%(name)s" id="%(name)s_iframe_result" type="hidden" />
""" % locals()

