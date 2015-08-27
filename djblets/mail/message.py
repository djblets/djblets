from __future__ import unicode_literals

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import six
from django.utils.datastructures import MultiValueDict


class EmailMessage(EmailMultiAlternatives):
    """An EmailMesssage subclass with improved header and message ID support.

    This class knows about several headers (standard and variations), including
    ``Sender``/``X-Sender``, ``In-Reply-To``/``References``, and ``Reply-To``.

    The generated ``Message-ID`` header from the e-mail can be accessed via the
    :py:attr:`message_id` attribute after the e-mail has been sent.

    This class also supports repeated headers.
    """

    def __init__(self, subject, text_body, html_body, from_email, to, cc=None,
                 sender=None, in_reply_to=None, headers=None,
                 auto_generated=False, prevent_auto_responses=False):
        """Create a new EmailMessage.

        Args:
            subject (unicode):
                The subject of the message.

            text_body (unicode):
                The body of the e-mail as plain text.

            html_body (unicode):
                The body of the e-mail as HTML.

            from_email (unicode):
                The from address.

            to (list):
                A list of e-mail addresses as :py:class:`unicode` objects that
                are to receive the e-mail.

            cc (list)
                A list of e-mail addresses as :py:class:`unicode` objects that
                are to receive a carbon copy of the e-mail, or ``None`` if
                there are no CC recipients.

            in_reply_to (unicode):
                An optional message ID (which will be used as the value for the
                ``In-Reply-To`` and ``References`` headers). This will be
                generated if not provided and will be available as the
                :py:attr:`message_id` attribute after the e-mail has been sent.

            headers (django.utils.datastructures.MultiValueDict):
                Extra headers to provide with the e-mail.

            auto_generated (bool):
                If ``True``, the e-mail will contain headers that mark it as
                an auto-generated message (as per RFC 3834) to avoid auto
                replies.

            prevent_auto_responses (bool):
                If ``True``, the e-mail will contain headers to prevent auto
                replies for delivery reports, read receipts, out of office
                e-mails, and other auto-generated e-mails from Exchange.
        """

        headers = headers or MultiValueDict()

        if (isinstance(headers, dict) and
            not isinstance(headers, MultiValueDict)):
            # Instantiating a MultiValueDict from a dict does not ensure that
            # values are lists, so we have to ensure that ourselves.
            headers = MultiValueDict(dict(
                (key, [value])
                for key, value in six.iteritems(headers)
            ))

        if sender:
            headers['Sender'] = sender
            headers['X-Sender'] = sender

        if in_reply_to:
            headers['In-Reply-To'] = in_reply_to
            headers['References'] = in_reply_to

        headers['Reply-To'] = from_email

        if auto_generated:
            headers['Auto-Submitted'] = 'auto-generated'

        if prevent_auto_responses:
            headers['X-Auto-Response-Suppress'] = 'DR, RN, OOF, AutoReply'

        super(EmailMessage, self).__init__(
            subject, text_body, settings.DEFAULT_FROM_EMAIL, to,
            headers={
                'From': from_email,
            })

        self.cc = cc or []
        self.message_id = None

        # We don't want to use the regular extra_headers attribute because
        # it will be treated as a plain dict by Django. Instead, since we're
        # using a MultiValueDict, we store it in a separate attribute
        # attribute and handle adding our headers in the message method.
        self._headers = headers

        self.attach_alternative(html_body, 'text/html')

    def message(self):
        msg = super(EmailMessage, self).message()
        self.message_id = msg['Message-ID']

        for name, value_list in self._headers.iterlists():
            for value in value_list:
                msg.add_header(six.binary_type(name), value)

        return msg

    def recipients(self):
        """Return a list of all recipients of the e-mail."""
        return self.to + self.bcc + self.cc
