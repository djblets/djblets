"""E-mail message composition and sending."""

from __future__ import annotations

import logging
from email.utils import parseaddr
from typing import Dict, Optional, Sequence, TYPE_CHECKING, Union

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_str
from housekeeping import deprecate_non_keyword_only_args

from djblets.deprecation import RemovedInDjblets60Warning
from djblets.mail.dmarc import is_email_allowed_by_dmarc
from djblets.mail.utils import build_email_address_via_service

if TYPE_CHECKING:
    from django.core.mail.message import SafeMIMEText


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
    ``from_spoofing`` (or set ``settings.DJBLETS_EMAIL_FROM_SPOOFING``). When
    set, the e-mail address used for the :mailheader:`From` header will only be
    used if there aren't any DMARC rules that may prevent the e-mail from being
    sent/received.

    .. note::

       Releases prior to Djblets 1.0.10 required using
       ``enable_smart_spoofing`` or ``settings.EMAIL_ENABLE_SMART_SPOOFING``,
       which didn't allow From spoofing to be completely disabled.)

    In the event that a DMARC rule would prevent sending on behalf of that
    user, the ``sender`` address will be used instead, with the full name
    appearing as the value in ``from_email`` with "via <Service Name>" tacked
    onto it.

    Callers wishing to use this should also set
    ``settings.EMAIL_DEFAULT_SENDER_SERVICE_NAME`` to the desired service name.
    Otherwise, the domain on the sender e-mail will be used instead.

    This class also supports repeated headers.

    Version Changed:
        1.0.10:
        Added the ``from_spoofing`` parameter and
        ``settings.DJBLETS_EMAIL_FROM_SPOOFING`` to replace
        ``enable_smart_spoofing`` and ``settings.EMAIL_ENABLE_SMART_SPOOFING``.
    """

    #: Always spoof the From address for a user.
    FROM_SPOOFING_ALWAYS = 'always'

    #: Only spoof the From address for a user if allowed by DMARC rules.
    FROM_SPOOFING_SMART = 'smart'

    #: Never spoof the From address for a user.
    FROM_SPOOFING_NEVER = 'never'

    ######################
    # Instance variables #
    ######################

    #: The stored Message-ID of the sent e-mail.
    message_id: Optional[str]

    #: Extra multi-value headers to apply to the message.
    _headers: MultiValueDict[str, str]

    @deprecate_non_keyword_only_args(RemovedInDjblets60Warning)
    def __init__(
        self,
        *,
        subject: str = '',
        text_body: str = '',
        html_body: str = '',
        from_email: Optional[str] = None,
        to: Optional[Sequence[str]] = None,
        cc: Optional[Sequence[str]] = None,
        bcc: Optional[Sequence[str]] = None,
        sender: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        headers: Optional[Union[Dict[str, str],
                                MultiValueDict[str, str]]] = None,
        auto_generated: bool = False,
        prevent_auto_responses: bool = False,
        from_spoofing: Optional[str] = None,
        enable_smart_spoofing: Optional[bool] = None,
        reply_to: Optional[Sequence[str]] = None,
    ) -> None:
        """Create a new EmailMessage.

        Args:
            subject (str, optional):
                The subject of the message.

                Defaults to being blank (which MTAs might replace with "no
                subject".)

            text_body (str, optional):
                The body of the e-mail as plain text.

                Defaults to an empty string (allowing HTML-only e-mails to be
                sent).

            html_body (str, optional):
                The body of the e-mail as HTML.

                Defaults to an empty string (allowing text-only e-mails to be
                sent).

            from_email (str, optional):
                The from address for the e-mail.

                Defaults to :django:setting:`DEFAULT_FROM_EMAIL`.

            to (list, optional):
                A list of e-mail addresses that are to receive the e-mail.

                Defaults to an empty list of addresses (allowing using CC/BCC
                only).

            cc (list, optional):
                A list of e-mail addresses that are to receive a carbon copy
                of the e-mail, or ``None`` if there are no CC recipients.

            bcc (list, optional):
                A list of e-mail addresses that are to receive a blind carbon
                copy of the e-mail, or ``None`` if there are not BCC
                recipients.

            sender (str, optional):
                The actual e-mail address sending this e-mail, for use in
                the :mailheader:`Sender` header.

                If this differs from ``from_email``, it will be left out of the
                header as per :rfc:`2822`.

                This will default to :django:setting:`DEFAULT_FROM_EMAIL`
                if unspecified.

            in_reply_to (str, optional):
                An optional message ID (which will be used as the value for the
                :mailheader:`In-Reply-To` and :mailheader:`References`
                headers).

                This will be generated if not provided and will be available as
                the :py:attr:`message_id` attribute after the e-mail has been
                sent.

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

            from_spoofing (str, optional):
                Optional behavior for spoofing a user's e-mail address in the
                :mailheader:`From` header.

                This can be one of :py:attr:`FROM_SPOOFING_ALWAYS`,
                :py:attr:`FROM_SPOOFING_SMART`, or
                :py:attr:`FROM_SPOOFING_NEVER`.

                This defaults to ``None``, in which case the
                ``enable_smart_spoofing`` will be checked (for legacy reasons),
                falling back to ``settings.DJBLETS_EMAIL_FROM_SPOOFING`` (which
                defaults to :py:attr:`FROM_SPOOFING_ALWAYS`, also for legacy
                reasons).

            enable_smart_spoofing (bool, optional):
                Whether to enable smart spoofing of any e-mail addresses for
                the :mailheader:`From` header (if ``from_spoofing`` is
                ``None``).

                This defaults to ``settings.EMAIL_ENABLE_SMART_SPOOFING``.

                This is deprecated in favor of ``from_spoofing``.

                Deprecated:
                    4.0:
                    This will be removed in Djblets 6.

            reply_to (str, optional):
                An explicit user used for the :mailheader:`Reply-To` header.

                If not provided, this defaults to ``from_email`` (if provided).

                Version Added:
                    4.0
        """
        headers = headers or MultiValueDict()

        if (isinstance(headers, dict) and
            not isinstance(headers, MultiValueDict)):
            # Instantiating a MultiValueDict from a dict does not ensure that
            # values are lists, so we have to ensure that ourselves.
            headers = MultiValueDict({
                key: [value]
                for key, value in headers.items()
            })

        if in_reply_to:
            headers['In-Reply-To'] = in_reply_to
            headers['References'] = in_reply_to

        if not reply_to and from_email:
            reply_to = [from_email]

        if from_spoofing is None:
            if enable_smart_spoofing is None:
                enable_smart_spoofing = \
                    getattr(settings, 'EMAIL_ENABLE_SMART_SPOOFING', None)

            if enable_smart_spoofing is not None:
                RemovedInDjblets60Warning.warn(
                    'settings.EMAIL_ENABLE_SMART_SPOOFING and the '
                    'enable_smart_spoofing argument to '
                    'djblets.mail.message.MailMessage are deprecated, and '
                    'will be removed in Djblets 6. Pleaase use '
                    'settings.DJBLETS_EMAIL_FROM_SPOOFING and the '
                    'from_spoofing= argument instead.')

                if enable_smart_spoofing:
                    from_spoofing = self.FROM_SPOOFING_SMART
                else:
                    # This was the original behavior when the setting was
                    # False.
                    from_spoofing = self.FROM_SPOOFING_ALWAYS

            if from_spoofing is None:
                from_spoofing = getattr(settings,
                                        'DJBLETS_EMAIL_FROM_SPOOFING',
                                        self.FROM_SPOOFING_ALWAYS)

        # Figure out the From/Sender we'll be wanting to use.
        if not from_email:
            sender = settings.DEFAULT_FROM_EMAIL

        if not sender:
            sender = settings.DEFAULT_FROM_EMAIL

        if sender == from_email:
            # RFC 2822 section 3.6.2 states that we should only include Sender
            # if the two are not equal. We also know that we're not spoofing,
            # so e-mail sending should work fine here.
            sender = None
        elif from_spoofing != self.FROM_SPOOFING_ALWAYS:
            # If from_spoofing is in smart mode, we will be checking the
            # DMARC record from the e-mail address we'd be ideally sending on
            # behalf of. If the record indicates that the message has any
            # likelihood of being quarantined or rejected, we'll alter the From
            # field to send using our Sender address instead.
            #
            # If from_spoofing is disabled, we will be changing the from_email
            # to avoid spoofing.
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
            # check if this e-mail could get lost due to the DMARC rules
            # or if from_spoofing is disabled.
            if (from_spoofing == self.FROM_SPOOFING_NEVER or
                (parsed_from_email != parsed_sender_email and
                 not is_email_allowed_by_dmarc(parsed_from_email))):
                # Spoofing is disabled or we can't spoof the e-mail address,
                # so instead, we'll keep the e-mail in Reply To and create a
                # From address we own, which will also indicate what service
                # is sending on behalf of the user.
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
        message_headers: Dict[str, str] = {}

        if from_email:
            message_headers['From'] = from_email

        super().__init__(
            subject=subject,
            body=force_str(text_body),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            headers=message_headers)

        self.message_id = None

        # We don't want to use the regular extra_headers attribute because
        # it will be treated as a plain dict by Django. Instead, since we're
        # using a MultiValueDict, we store it in a separate attribute
        # attribute and handle adding our headers in the message method.
        self._headers = headers

        if html_body:
            self.attach_alternative(force_str(html_body), 'text/html')

    def message(self) -> SafeMIMEText:
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
        msg = super().message()
        self.message_id = msg['Message-ID']

        for name, value_list in self._headers.lists():
            for value in value_list:
                # Use the native string on each version of Python. These
                # are headers, so they'll be convertible without encoding
                # issues.
                msg[name] = value

        return msg
