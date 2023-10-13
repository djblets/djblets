"""Specialized HTTP response classes.

Version Added:
    4.0
"""

from __future__ import annotations

from typing import Callable, Iterator, List, Optional, TYPE_CHECKING, Union

from django.http.response import StreamingHttpResponse
from typing_extensions import NotRequired, TypeAlias, TypedDict

if TYPE_CHECKING:
    from django.http import HttpRequest


class EventStreamMessage(TypedDict):
    """A message in an event stream.

    One message may contain an ID, application-defined event type, serialized
    payload data, and a retry time in milliseconds. These are all optional,
    but any empty message will be skipped.

    Version Added:
        4.0
    """

    #: The payload data to send.
    #:
    #: This will be sent as the ``data`` field.
    #:
    #: Type:
    #:     bytes or str
    data: NotRequired[Optional[Union[bytes, str]]]

    #: The event name to send.
    #:
    #: This will be sent as the ``event`` field.
    #:
    #: Type:
    #:     str
    event: NotRequired[Optional[str]]

    #: The ID to send.
    #:
    #: This will be sent as the ``id`` field.
    #:
    #: Type:
    #:     str
    id: NotRequired[Optional[str]]

    #: The retry time in milliseconds for reconnections after a disconnect.
    #:
    #: This will be sent as the ``retry`` field.
    #:
    #: Type:
    #:     int
    retry_ms: NotRequired[Optional[int]]


#: An iterator for event stream messages.
#:
#: Version Added:
#:     4.0
EventStreamMessages: TypeAlias = Iterator[EventStreamMessage]


#: An event stream that generates messages.
#:
#: This may be an iterator of messages, or a callable that takes an optional
#: :mailheader:`Last-Event-ID` header value and then yields messages.
#:
#: Version Added:
#:     4.0
EventStream: TypeAlias = Union[
    EventStreamMessages,
    Callable[[Optional[str]], EventStreamMessages],
]


class EventStreamHttpResponse(StreamingHttpResponse):
    """A Server-Sent Events (SSE) HTTP response.

    This manages a response containing Server-Sent Events, which can be
    used to continuously stream content (events, data, IDs, and retry
    intervals) to a caller in a standardized way.

    Server-Sent Events are useful for long-running, resumeable process, such
    as conveying progress for long-running but interruptible operations,
    new updates to content, or events on a message bus.

    Providers of SSE responses can use the :mailheader:`Last-Event-ID` header
    value to determine where the client left off, and resume from that point.
    If a function is passed as the event stream source, it will receive any
    value in this header as an argument.

    Note:
        On HTTP/1.1 connections, web browsers are limited to 6 concurrent HTTP
        connections to the same domain across all tabs, and a long-running SSE
        stream will consume one of those slots until it ends.

        HTTP/2 connections have a higher limit.

        For widest compatibility when serving over HTTP/1.1 connections, it's
        recommended to use shorter-lived, resumeable SSE responses.

    Version Added:
        4.0
    """

    streaming = True

    ######################
    # Instance variables #
    ######################

    #: The event stream providing values for the response.
    #:
    #: Type:
    #:     callable or generator
    event_stream: EventStream

    #: The HTTP request from the client, if provided to the response.
    #:
    #: Type:
    #:     django.http.HttpRequest
    request: Optional[HttpRequest]

    def __init__(
        self,
        event_stream: EventStream,
        *,
        request: Optional[HttpRequest] = None,
        status: int = 200,
        content_type: str = 'text/event-stream',
        **kwargs,
    ) -> None:
        """Initialize the event stream.

        The provided event stream source will be processed when sending
        content to the client, and not before.

        Args:
            event_stream (callable or generator):
                The event stream as a generator or a callable yielding
                results.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            status (int, optional):
                The HTTP status code to send in the response.

            content_type (str, optional):
                The content type to send in the response.

                For greatest compatibility, this should be left as the
                default of :mimetype:`text/event-stream`.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent
                constructor.
        """
        self.event_stream = event_stream
        self.request = request

        super().__init__(self._process_events(),
                         status=status,
                         content_type=content_type,
                         **kwargs)

        self['Cache-Control'] = 'no-cache'

        # It's important that we disable any encodings, or the GZip middleware
        # will try to compress multiple messages at once and delay sending
        # them until there's a suitably-compressed segment. This happens in
        # GZipMiddleware and in django.utils.text.compress_sequence.
        #
        # Ideally we'd just tell it to flush per-message, but we can't. We
        # can do our own compression if the middleware is installed, manually
        # handling all compression via django.utils.text.compress_string()
        # if `Accept-Encoding:` includes "gzip", and that's worth considering
        # in the future, but may not ultimately be worth it given the size
        # of the small messages being sent.
        self['Content-Encoding'] = ''

    def _process_events(self) -> Iterator[bytes]:
        """Generate serialized messages based on the event stream.

        This will iterate through the response's event stream, converting
        any messages to serialized Server-Sent Event data.

        This can only be called once per response instance.

        Yields:
            bytes:
            Each serialized message to send to the client.
        """
        make_bytes = self.make_bytes
        event_stream = self.event_stream

        if callable(event_stream):
            last_id: Optional[str]
            request = self.request

            if request is not None:
                last_id = request.META.get('HTTP_LAST_EVENT_ID')
            else:
                last_id = None

            event_stream = event_stream(last_id)

        for message in event_stream:
            if message:
                data = message.get('data')
                event = message.get('event')
                message_id = message.get('id')
                retry = message.get('retry_ms')

                payload: List[bytes] = []

                if message_id is not None:
                    if message_id == '':
                        # This will reset the ID for the Last-Event-ID header.
                        payload.append(b'id\n')
                    else:
                        payload.append(b'id: %s\n' % make_bytes(message_id))

                if event is not None:
                    payload.append(b'event: %s\n' % make_bytes(event))

                if data is not None:
                    payload += [
                        b'data: %s\n' % make_bytes(line)
                        for line in data.splitlines()
                    ]

                if retry is not None:
                    payload.append(b'retry: %d\n' % retry)

                payload.append(b'\n')

                yield b''.join(payload)
            else:
                # This is a no-op, but will keep the connection open.
                yield b':\n\n'
