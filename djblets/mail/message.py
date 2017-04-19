"""E-mail message composition and sending."""

from __future__ import unicode_literals

import logging
from email.utils import parseaddr

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import six
from django.utils.datastructures import MultiValueDict

from djblets.mail.dmarc import is_email_allowed_by_dmarc
from djblets.mail.utils import build_email_address_via_service


logger = logging.getLogger(__name__)


class EmailMessage(EmailMultiAlternatives):
    """An EmailMesssage subclass with improved header and message ID support.

    This class knows about several headers (standard and variations), including
    :mailheader:`Sender`/:mailheader:`X-Sender`,
    :mailheader:`In-Reply-To`/:mailheader:`References``, and
    :mailheader:`Reply-To`.

    The generated :mailheader:`Message-ID` header from the e-mail can be
    accessed via the :py:attr:`message_id` attribute after the e-mail has been
    sent.

    In order to prevent issues when sending on behalf of users whose e-mail
    domains are controlled by DMARC, callers can specify
    ``enable_smart_spoofing=True`` (or set
    ``settings.EMAIL_ENABLE_SMART_SPOOFING``). If set, then the e-mail address
    used for the :mailheader:`From` header will only be used if there aren't
    any DMARC rules that may prevent the e-mail from being sent/received.

    In the event that a DMARC rule would prevent sending on behalf of that
    user, the ``sender`` address will be used instead, with the full name
    appearing as the value in ``from_email`` with "via <Service Name>" tacked
    onto it.

    Callers wishing to use this should also set
    ``settings.EMAIL_DEFAULT_SENDER_SERVICE_NAME`` to the desired service name.
    Otherwise, the domain on the sender e-mail will be used instead.

    This class also supports repeated headers.
    """

    def __init__(self, subject='', text_body='', html_body='', from_email=None,
                 to=None, cc=None, bcc=None, sender=None, in_reply_to=None,
                 headers=None, auto_generated=False,
                 prevent_auto_responses=False, enable_smart_spoofing=None):
        """Create a new EmailMessage.

        Args:
            subject (unicode, optional):
                The subject of the message. Defaults to being blank (which
                MTAs might replace with "no subject".)

            text_body (unicode, optional):
                The body of the e-mail as plain text. Defaults to an empty
                string (allowing HTML-only e-mails to be sent).

            html_body (unicode, optional):
                The body of the e-mail as HTML. Defaults to an empty string
                (allowing text-only e-mails to be sent).

            from_email (unicode, optional):
                The from address for the e-mail. Defaults to
                :django:setting:`DEFAULT_FROM_EMAIL`.

            to (list, optional):
                A list of e-mail addresses as :py:class:`unicode` objects that
                are to receive the e-mail. Defaults to an empty list of
                addresses (allowing using CC/BCC only).

            cc (list, optional):
                A list of e-mail addresses as :py:class:`unicode` objects that
                are to receive a carbon copy of the e-mail, or ``None`` if
                there are no CC recipients.

            bcc (list, optional):
                A list of e-mail addresses as :py:class:`unicode` objects that
                are to receive a blind carbon copy of the e-mail, or ``None``
                if there are not BCC recipients.

            sender (unicode, optional):
                The actual e-mail address sending this e-mail, for use in
                the :mailheader:`Sender` header. If this differs from
                ``from_email``, it will be left out of the header as per
                :rfc:`2822`.

                This will default to :django:setting:`DEFAULT_FROM_EMAIL`
                if unspecified.

            in_reply_to (unicode, optional):
                An optional message ID (which will be used as the value for the
                :mailheader:`In-Reply-To` and :mailheader:`References`
                headers). This will be generated if not provided and will be
                available as the :py:attr:`message_id` attribute after the
                e-mail has been sent.

            headers (django.utils.datastructures.MultiValueDict, optional):
                Extra headers to provide with the e-mail.

            auto_generated (bool, optional):
                If ``True``, the e-mail will contain headers that mark it as
                an auto-generated message (as per :rfc:`3834`) to avoid auto
                replies.

            prevent_auto_responses (bool, optional):
                If ``True``, the e-mail will contain headers to prevent auto
                replies for delivery reports, read receipts, out of office
                e-mails, and other auto-generated e-mails from Exchange.

            enable_smart_spoofing (bool, optional):
                Whether to enable smart spoofing of any e-mail addresses for
                the :mailheader:`From` header.

                This defaults to ``settings.EMAIL_ENABLE_SMART_SPOOFING``
                (which itself defaults to ``False``).
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

        if in_reply_to:
            headers['In-Reply-To'] = in_reply_to
            headers['References'] = in_reply_to

        headers['Reply-To'] = from_email

        if enable_smart_spoofing is None:
            enable_smart_spoofing = \
                getattr(settings, 'EMAIL_ENABLE_SMART_SPOOFING', False)

        # Figure out the From/Sender we'll be wanting to use.
        if not sender:
            sender = settings.DEFAULT_FROM_EMAIL

        if sender == from_email:
            # RFC 2822 section 3.6.2 states that we should only include Sender
            # if the two are not equal. We also know that we're not spoofing,
            # so e-mail sending should work fine here.
            sender = None
        elif enable_smart_spoofing:
            # We will be checking the DMARC record from the e-mail address
            # we'd be ideally sending on behalf of. If the record indicates
            # that the message has any likelihood of being quarantined or
            # rejected, we'll alter the From field to send using our Sender
            # address instead.
            parsed_from_name, parsed_from_email = parseaddr(from_email)
            parsed_sender_name, parsed_sender_email = parseaddr(sender)

            # The above will return ('', '') if the address couldn't be parsed,
            # so check for this.
            if not parsed_from_email:
                logger.warning('EmailMessage: Unable to parse From address '
                               '"%s"',
                               from_email)

            if not parsed_sender_email:
                logger.warning('EmailMessage: Unable to parse Sender address '
                               '"%s"',
                               sender)

            # We may not be allowed to send on behalf of this user.
            # We actually aren't going to check for this (it may be due
            # to SPF, which is too complex for us to want to check, or
            # it may be due to another ruleset somewhere). Instead, just
            # check if this e-mail could get lost due to the DMARC rules.
            if (parsed_from_email != parsed_sender_email and
                not is_email_allowed_by_dmarc(parsed_from_email)):
                # We can't spoof the e-mail address, so instead, we'll keep
                # the e-mail in Reply To and create a From address we own,
                # which will also indicate what service is sending on behalf
                # of the user.
                from_email = build_email_address_via_service(
                    full_name=parsed_from_name,
                    email=parsed_from_email,
                    sender_email=parsed_sender_email)

        if sender:
            headers['Sender'] = sender
            headers['X-Sender'] = sender

        if auto_generated:
            headers['Auto-Submitted'] = 'auto-generated'

        if prevent_auto_responses:
            headers['X-Auto-Response-Suppress'] = 'DR, RN, OOF, AutoReply'

        # We're always going to explicitly send with the DEFAULT_FROM_EMAIL,
        # but replace the From header with the e-mail address we decided on.
        # While this class and its parent classes don't really care about the
        # difference between these, Django's SMTP e-mail sending machinery
        # treats them differently, sending the value of EmailMessage.from_email
        # when communicating with the SMTP server.
        super(EmailMessage, self).__init__(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
            cc=cc,
            bcc=bcc,
            headers={
                'From': from_email,
            })

        self.message_id = None

        # We don't want to use the regular extra_headers attribute because
        # it will be treated as a plain dict by Django. Instead, since we're
        # using a MultiValueDict, we store it in a separate attribute
        # attribute and handle adding our headers in the message method.
        self._headers = headers

        if html_body:
            self.attach_alternative(html_body, 'text/html')

    def message(self):
        """Construct an outgoing message for the e-mail.

        This will construct a message based on the data provided to the
        constructor. This represents the e-mail that will later be sent using
        :py:meth:`send`.

        After calling this method, the message's ID will be stored in the
        :py:attr:`message_id` attribute for later reference.

        This does not need to be called manually. It's called by
        :py:meth:`send`.

        Returns:
            django.core.mail.message.SafeMIMEText:
            The resulting message.
        """
        msg = super(EmailMessage, self).message()
        self.message_id = msg['Message-ID']

        for name, value_list in self._headers.iterlists():
            for value in value_list:
                msg.add_header(six.binary_type(name), value)

        return msg

    def recipients(self):
        """Return a list of all recipients of the e-mail.

        Returns:
            list:
            A list of all recipients included on the To, CC, and BCC lists.
        """
        return self.to + self.bcc + self.cc
