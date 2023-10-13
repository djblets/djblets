"""HTTP responses for Web APIs."""

from __future__ import annotations

from typing import (Any, Callable, Collection, Dict, Iterator, List, Optional,
                    Sequence, TYPE_CHECKING, Union)

from django.http import HttpResponse
from django.utils.encoding import force_str
from typing_extensions import NotRequired, TypeAlias, TypedDict

from djblets.http.responses import (EventStreamMessage,
                                    EventStreamMessages,
                                    EventStreamHttpResponse)
from djblets.util.http import (get_http_requested_mimetype,
                               get_url_params_except,
                               is_mimetype_a)
from djblets.webapi.encoders import (JSONEncoderAdapter, WebAPIEncoder,
                                     XMLEncoderAdapter,
                                     get_registered_encoders)
from djblets.webapi.errors import INVALID_FORM_DATA


if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.forms import Form
    from django.http import HttpRequest

    from djblets.webapi.errors import WebAPIError


#: A dictionary of headers to return from the API.
#:
#: Version Added:
#:     3.2
WebAPIResponseHeaders: TypeAlias = Dict[str, str]


class WebAPIResponseLink(TypedDict):
    """Dictionary containing information on a link.

    Version Added:
        3.2
    """

    #: The HTTP method used to access the link.
    #:
    #: Type:
    #:     str
    method: str

    #: The absolute URL that the link points to.
    #:
    #: This may be None in the case of an error generating a link, such as
    #: due to a circular dependency.
    #:
    #: Version Changed:
    #:     4.0:
    #:     This can now be ``None``.
    #:
    #: Type:
    #:     str
    href: Optional[str]

    #: The optional title for the link.
    #:
    #: This may not be present in the dictionary.
    #:
    #: Type:
    #:     str
    title: NotRequired[str]


#: A type alias for a mapping of link names to link information.
#:
#: Version Added:
#:     3.2
WebAPIResponseLinks: TypeAlias = Dict[str, WebAPIResponseLink]


#: A type alias for an API response payload.
#:
#: Version Added:
#:     3.2
WebAPIResponsePayload: TypeAlias = Dict[Any, Any]


class WebAPIEventStreamMessage(EventStreamMessage):
    """A message generated in an API event stream.

    This is used by :py:class:`WebAPIResponseEventStream` to stream data to
    a client.

    A message may contain an ID, application-defined event type, serialized
    payload data (which may be a serialized object payload or may be custom
    text-based data), and a retry time in milliseconds. These are all optional,
    but any empty message will be skipped.

    Version Added:
        4.0
    """

    #: An API response payload to send in the message.
    #:
    #: Type:
    #:     dict
    obj: NotRequired[WebAPIResponsePayload]

    #: The value for the API response payload's ``stat`` key.
    #:
    #: If not provided, this will default to "ok".
    #:
    #: Type:
    #:     str
    stat: NotRequired[str]


#: An iterator for API event stream messages.
#:
#: Version Added:
#:     4.0
WebAPIEventStreamMessages: TypeAlias = Iterator[WebAPIEventStreamMessage]


#: An API event stream that generates messages.
#:
#: This may be an iterator of messages, or a callable that takes an optional
#: :mailheader:`Last-Event-ID` header value and then yields messages.
#:
#: Version Added:
#:     4.0
WebAPIEventStream: TypeAlias = Union[
    WebAPIEventStreamMessages,
    Callable[[Optional[str]], WebAPIEventStreamMessages],
]


class WebAPIResponse(HttpResponse):
    """An API response, formatted for the desired file format."""

    #: The default list of supported mimetypes for the payload.
    #:
    #: Type:
    #:     list of str
    supported_mimetypes: List[str] = [
        'application/json',
        'application/xml',
    ]

    ######################
    # Instance variables #
    ######################

    #: The response payload that will be encoded.
    #:
    #: This will be made up of both default and caller-provided data.
    #:
    #: Type:
    #:     dict
    api_data: WebAPIResponsePayload

    #: A JSONP callback provided in GET requests.
    #:
    #: This will be set if the caller specifies ``?callback=...``. Otherwise,
    #: it will be ``None``.
    #:
    #: Type:
    #:     str
    callback: Optional[str]

    #: Whether :py:attr:`content` has been computed for the final result.
    #:
    #: This is mostly an implementation detail, but is available to outside
    #: callers to know when the content is finalized.
    #:
    #: Type:
    #:     bool
    content_set: bool

    #: The list of encoders that can be used to try to encode the payload.
    #:
    #: Type:
    #:     list of djblets.webapi.encoders.WebAPIEncoder
    encoders: Sequence[WebAPIEncoder]

    #: Keyword arguments to pass to the encoders.
    #:
    #: Type:
    #:     dict
    encoder_kwargs: Dict[str, Any]

    #: The mimetype used for the response.
    #:
    #: Type:
    #:     str
    mimetype: str

    #: The HTTP request from the client.
    #:
    #: Type:
    #:     django.http.HttpRequest
    request: HttpRequest

    def __init__(
        self,
        request: HttpRequest,
        *,
        obj: WebAPIResponsePayload = {},
        stat: str = 'ok',
        api_format: Optional[str] = None,
        status: int = 200,
        headers: WebAPIResponseHeaders = {},
        encoders: Sequence[WebAPIEncoder] = [],
        encoder_kwargs: Dict[str, Any] = {},
        mimetype: Optional[str] = None,
        supported_mimetypes: Optional[List[str]] = None,
    ) -> None:
        """Initialize the response.

        This will attempt to automatically determine the resulting mimetype,
        if ``mimetype`` is not provided.

        If ``api_format`` is provided (as an argument to this function, through
        the ``api_format=`` query string for GET requests, or through a field
        for POST/PUT requests), it will be used to try to guess the mimetype.

        If one cannot be determined through those values, the
        :mailheader:`Accept` HTTP header will be used instead.

        Finally, if no mimetype can be determined, no content will be generated
        and this will automatically be set to a :http:`400`.

        Version Changed:
            3.2:
            All arguments (except for ``request``) must now be provided as
            keywords.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            obj (dict, optional):
                The object payload to serializle.

                Contents depends on the ``encoder``.

            stat (str, optional):
                The value for the API response payload's ``stat`` key.

            api_format (str, optional):
                An explicit format for the result payload, used to determine
                a default for :py:attr:`mimetype`.

            status (int, optional):
                The HTTP status code for the response.

            headers (dict, optional):
                Custom HTTP headers to include in the response.

            encoders (list of djblets.webapi.encoders.WebAPIEncoder, optional):
                The list of encoders available to encode ``obj``.

                If not provided, all registered encoders will be tried. See
                :py:func:`~djblets.webapi.encoders.get_registered_encoders`.

            encoder_kwargs (dict, optional):
                Keyword arguments to pass when instantiating encoders.

            mimetype (str, optional):
                An explicit mimetype to use for the result.

            supported_mimetypes (list of str, optional):
                A list of supported mimetypes for this response.

                This is used when trying to guess a mimetype from the
                :mailheader:`Accept` header.
        """
        mimetype = _normalize_response_mimetype(
            request=request,
            mimetype=mimetype,
            api_format=api_format,
            supported_mimetypes=(supported_mimetypes or
                                 self.supported_mimetypes))

        if not mimetype:
            self.status_code = 400
            self.content_set = True
            return

        super().__init__(content_type=mimetype,
                         status=status)
        self.request = request
        self.callback = request.GET.get('callback', None)
        self.api_data = {'stat': stat}
        self.api_data.update(obj)
        self.content_set = False
        self.mimetype = mimetype
        self.encoders = encoders or get_registered_encoders()
        self.encoder_kwargs = encoder_kwargs

        for header, value in headers.items():
            self[header] = value

        # Prevent IE8 from trying to download some AJAX responses as if they
        # were files.
        self['X-Content-Type-Options'] = 'nosniff'

    # Note: We're overriding HttpResponse.content, which in Django is untyped
    #       and in the django-stubs package is typed with a utility object.
    #       Because of this, we can't easily maintain signature compatibility,
    #       meaning type checkers will yell at us.
    #
    #       Also, while the getter will return a byte string, the setter will
    #       accept anything. Type checkers seem to be confused by this.
    #
    #       This is why we're using `type: ignore` here and below:
    #
    @property                    # type: ignore
    def content(self) -> bytes:  # type: ignore
        """The encoded API response content.

        This is an overridden version of :py:meth:`HttpResponse._get_content()
        <django.http.HttpResponse._get_content>` that generates the resulting
        content when requested, rather than generating it up-front in the
        constructor, allowing data to be updated after construction but before
        it's ready to be sent to the client.

        Type:
            bytes
        """
        class MultiEncoder(WebAPIEncoder):
            def __init__(
                self,
                encoders: Sequence[WebAPIEncoder],
            ) -> None:
                self.encoders = encoders

            def encode(self, *args, **kwargs) -> str:
                for encoder in self.encoders:
                    result = encoder.encode(*args, **kwargs)

                    if result is not None:
                        return result

                return ''

        if not self.content_set:
            adapter: Optional[Union[JSONEncoderAdapter,
                                    XMLEncoderAdapter]] = None
            encoder = MultiEncoder(self.encoders)

            # See the note above about the check for text/plain.
            if (self.mimetype == 'text/plain' or
                is_mimetype_a(self.mimetype, 'application/json')):
                adapter = JSONEncoderAdapter(encoder)
            elif is_mimetype_a(self.mimetype, "application/xml"):
                adapter = XMLEncoderAdapter(encoder)

            assert adapter is not None
            content: str = adapter.encode(self.api_data,
                                          request=self.request,
                                          **self.encoder_kwargs)

            if self.callback is not None:
                content = f'{self.callback}({content});'

            self.content = content  # type: ignore
            self.content_set = True

        return super().content

    @content.setter
    def content(
        self,
        value: Any,
    ) -> None:
        """Set the content on the response.

        Args:
            value (object):
                The value to set.

                This will be converted to a byte string by Django.
        """
        # We need to call this on the class, which is why we're not using
        # `super()`.
        #
        # Note that type checkers would complain here, but this is correct.
        # Internally, `HttpResponse.content` can take various values and will
        # convert them as appropriate. The `django-stubs` module, if used,
        # incorrectly interprets `HttpResponse.content` as being `bytes`.
        HttpResponse.content.fset(self, value)  # type: ignore


class WebAPIResponsePaginated(WebAPIResponse):
    """A response containing a list of results with pagination.

    This accepts the following parameters to the URL:

    * start - The index of the first item (0-based index).
    * max-results - The maximum number of results to return in the request.

    Subclasses can override much of the pagination behavior of this function.
    While the default behavior operates on a queryset and works on indexes
    within that queryset, subclasses can override this to work on any data
    and paginate in any way they see fit.
    """

    ######################
    # Instance variables #
    ######################

    #: The maximum number of results that will be returned.
    #:
    #: Type:
    #:     int
    max_results: int

    #: The query argument key requesting the maximum number of results.
    #:
    #: Type:
    #:     str
    max_results_param: str

    #: The key used for the next results link in the payload.
    #:
    #: Type:
    #:     str
    next_key: str

    #: The key used for the previous results link in the payload.
    #:
    #: Type:
    #:     str
    prev_key: str

    #: The optional queryset used to construct these results.
    #:
    #: Type:
    #:     django.db.models.QuerySet
    queryset: Optional[QuerySet]

    #: The results to return.
    #:
    #: Type:
    #:     collections.abc.Collection
    results: Collection[Any]

    #: The starting offset for results.
    #:
    #: Type:
    #:     int
    start: int

    #: The query argument key requesting the start offset.
    #:
    #: Type:
    #:     str
    start_param: str

    #: The key used for the total results count in the payload.
    #:
    #: Type:
    #:     str
    total_results_key: str

    def __init__(
        self,
        request: HttpRequest,
        *args,
        queryset: Optional[QuerySet] = None,
        results_key: str = 'results',
        prev_key: str = 'prev',
        next_key: str = 'next',
        total_results_key: str = 'total_results',
        start_param: str = 'start',
        max_results_param: str = 'max-results',
        default_start: int = 0,
        default_max_results: int = 25,
        max_results_cap: int = 200,
        serialize_object_func: Optional[Callable[[object], Any]] = None,
        extra_data: Dict[Any, Any] = {},
        **kwargs,
    ) -> None:
        """Initialize the response.

        Version Changed:
            3.2:
            All arguments (except for ``request``) must now be provided as
            keywords.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            *args (tuple):
                Positional arguments to pass to the parent class.

                This is only for backwards-compatibility, and will be removed
                in Djblets 4.0.

            queryset (django.db.models.QuerySet, optional):
                The optional queryset used to construct these results.

            results_key (str, optional):
                The name of the key used to store the resulting list of items.

            prev_key (str, optional):
                The key used for the previous results link in the payload.

            next_key (str, optional):
                The key used for the next results link in the payload.

            total_results_key (str, optional):
                The key used for the total results count in the payload.

            start_param (str, optional):
                The query argument key requesting the start offset.

            max_results_param (str, optional):
                The query argument key requesting the maximum number of
                results.

            default_start (int, optional):
                The default start offset, if not provided in the request
                using ``start_param``.

            default_max_results (int, optional):
                The default maximum number of results, if not provided in
                the request using ``max_results_param``.

            max_results_cap (int, optional):
                The maximum number of results allowed in a response.

                Any user-requested max will be capped to this value.

            serialize_object_func (callable, optional):
                A function to call to serialize a single result.

            extra_data (dict, optional):
                Extra payload data to merge into the resulting payload.

            **kwargs (dict):
                Keyword arguments to pass to the parent class.
        """
        if 'obj' in kwargs:
            raise ValueError(f'obj= cannot be passed to {type(self)}')

        self.request = request
        self.queryset = queryset
        self.prev_key = prev_key
        self.next_key = next_key
        self.start_param = start_param
        self.max_results_param = max_results_param

        self.start = self.normalize_start(
            request.GET.get(start_param, default_start))

        try:
            self.max_results = \
                min(int(request.GET.get(max_results_param,
                                        default_max_results)),
                    max_results_cap)
        except ValueError:
            self.max_results = default_max_results

        self.results = self.get_results()
        self.total_results = self.get_total_results()

        if self.total_results == 0:
            self.results = []
        elif serialize_object_func:
            self.results = [
                serialize_object_func(obj)
                for obj in self.results
            ]
        else:
            self.results = list(self.results)

        data: WebAPIResponsePayload = {
            results_key: self.results,
            'links': {},
        }
        data.update(extra_data)

        links = data['links']
        assert isinstance(links, dict)
        links.update(self.get_links())

        if total_results_key and self.total_results is not None:
            data[total_results_key] = self.total_results

        super().__init__(request,
                         obj=data,
                         *args,
                         **kwargs)

    def normalize_start(
        self,
        start: Union[int, str],
    ) -> int:
        """Normalize the start value.

        By default, this ensures it's an integer no less than 0.
        Subclasses can override this behavior.

        Args:
            start (int or str):
                The requested starting offset.

        Returns:
            int:
            The normalized starting offset.
        """
        try:
            return max(int(start), 0)
        except ValueError:
            return 0

    def has_prev(self) -> bool:
        """Return whether there's a previous set of results.

        Returns:
            bool:
            ``True`` if there's a previous set of results. ``False`` if
            there is not.
        """
        return self.start > 0

    def has_next(self) -> bool:
        """Return whether there's a next set of results.

        Returns:
            bool:
            ``True`` if there's a next set of results. ``False`` if there
            is not.
        """
        return self.start + len(self.results) < self.total_results

    def get_prev_index(self) -> int:
        """Return the previous index to use for ?start=

        Returns:
            int:
            The previous index. This will never be less than 0.
        """
        return max(0, self.start - self.max_results)

    def get_next_index(self) -> int:
        """Return the next index to use for ?start=

        Returns:
            int:
            The next index.
        """
        return self.start + self.max_results

    def get_results(self) -> Collection[Any]:
        """Return the results for this page.

        Returns:
            collections.abc.Collection:
            The collection of results from the queryset.
        """
        if self.queryset is not None:
            return self.queryset[self.start:self.start + self.max_results]

        return []

    def get_total_results(self) -> int:
        """Return the total number of results across all pages.

        Subclasses can return ``None`` to prevent this field from showing up
        in the payload.

        Returns:
            int:
            The number of resulting items.
        """
        if self.queryset is not None:
            return self.queryset.count()

        return 0

    def get_links(self) -> WebAPIResponseLinks:
        """Return all links used in the payload.

        By default, this only includes pagination links. Subclasses can
        provide additional links.

        Returns:
            dict:
            The dictionary mapping link names to link information.

            See :py:class:`WebAPIResponseLinkDict` for the format of the link
            information dictionaries.
        """
        links: WebAPIResponseLinks = {}

        full_path = self.request.build_absolute_uri(self.request.path)

        query_parameters = get_url_params_except(
            self.request.GET, self.start_param, self.max_results_param)

        if query_parameters:
            query_parameters = f'&{query_parameters}'

        if self.has_prev():
            links[self.prev_key] = {
                'method': 'GET',
                'href': self.build_pagination_url(
                    full_path, self.get_prev_index(),
                    self.max_results, query_parameters),
            }

        if self.has_next():
            links[self.next_key] = {
                'method': 'GET',
                'href': self.build_pagination_url(
                    full_path, self.get_next_index(),
                    self.max_results, query_parameters),
            }

        return links

    def build_pagination_url(
        self,
        full_path: str,
        start: int,
        max_results: int,
        query_parameters: str,
    ) -> str:
        """Build a URL to go to the previous or next set of results.

        Args:
            full_path (str):
                The full path to the API endpoint.

            start (int):
                The start offset for the results.


            max_results (int):
                The maximum number of results to return.

            query_parameters (str):
                Additional query parameters to include in the query string.
                This must start with ``&``.
        """
        return (
            f'{full_path}'
            f'?{self.start_param}={start}'
            f'&{self.max_results_param}={max_results}'
            f'{query_parameters}'
        )


class WebAPIResponseError(WebAPIResponse):
    """A general API error response.

    This contains an error code and a human-readable message. Additional
    data can be provided through ``extra_params`` and ``headers``.
    """

    def __init__(
        self,
        request: HttpRequest,
        err: WebAPIError,
        *args,
        extra_params: Dict[Any, Any] = {},
        headers: WebAPIResponseHeaders = {},
        **kwargs,
    ) -> None:
        """Initialize the response.

        Version Changed:
            3.2:
            All arguments (except for ``request``) must now be provided as
            keywords.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            err (djblets.webapi.errors.WebAPIError):
                The error class to use for the response.

            *args (tuple):
                Positional arguments to pass to the parent class.

                This is only for backwards-compatibility, and will be removed
                in Djblets 4.0.

            extra_params (dict, optional):
                Additional data to include in the root of the payload.

                This should not include an ``err`` key.

            headers (dict, optional):
                Custom HTTP headers to include in the response.

            **kwargs (dict):
                Keyword arguments to pass to the parent class.
        """
        for arg in ('obj', 'stat', 'status'):
            if arg in kwargs:
                raise ValueError(f'{arg}= cannot be passed to {type(self)}')

        err_payload = {
            'code': err.code,
            'msg': err.msg,
        }

        if err.error_type:
            err_payload['type'] = err.error_type

            if err.error_subtype:
                err_payload['subtype'] = err.error_subtype

        if err.detail:
            err_payload['detail'] = err.detail

        if err.trace_id:
            err_payload['trace_id'] = err.trace_id

        errdata: WebAPIResponsePayload = {
            'err': err_payload,
        }
        errdata.update(extra_params)

        headers = headers.copy()

        if callable(err.headers):
            headers.update(err.headers(request))
        else:
            headers.update(err.headers)

        super().__init__(request,
                         obj=errdata,
                         stat='fail',
                         status=err.http_status,
                         headers=headers,
                         *args,
                         **kwargs)


class WebAPIResponseFormError(WebAPIResponseError):
    """An error response designed to return all errors from a form."""

    def __init__(
        self,
        request: HttpRequest,
        form: Form,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the response.

        Version Changed:
            3.2:
            All arguments (except for ``request``) must now be provided as
            keywords.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            form (django.forms.Form):
                The form class to represent in the response.

            *args (tuple):
                Positional arguments to pass to the parent class.

                This is only for backwards-compatibility, and will be removed
                in Djblets 4.0.

            **kwargs (dict):
                Keyword arguments to pass to the parent class.
        """
        for arg in ('error', 'extra_params'):
            if arg in kwargs:
                raise ValueError(f'{arg}= cannot be passed to {type(self)}')

        fields: Dict[str, List[str]] = {
            field: [force_str(e) for e in form.errors[field]]
            for field in form.errors
        }

        super().__init__(
            request,
            INVALID_FORM_DATA,
            extra_params={
                'fields': fields,
            },
            *args,
            **kwargs)


class WebAPIResponseEventStream(EventStreamHttpResponse):
    """A Server-Sent Events (SSE) API response.

    This is a specialization of
    :py:class:`~djblets.http.responses.EventStreamHttpResponse` built to
    serialize API responses as part of Server-Sent Events. This enables
    standard API responses to be serialized as results from an event stream,
    useful for streaming progress updates or batched API call results as part
    of an API call.

    By default, each Server-Sent Event will contain API payload data
    containing, at a minimum, a standard ``"stat": "ok"`` field. This can be
    extended by specifying an object payload. The serialized result of the
    payload will be in JSON format by default, but this can be controlled
    through the standard :mailheader:`Accept` header or ``api_format``
    argument.

    The mimetype for standard data payloads (for entries without an ``event``
    type or with ``event: message``, the spec-provided default) will be sent
    in :mailheader:`X-Event-Data-Mimetype`.

    Version Added:
        4.0
    """

    def __init__(
        self,
        event_stream: WebAPIEventStream,
        *,
        request: HttpRequest,
        api_format: Optional[str] = None,
        status: int = 200,
        headers: WebAPIResponseHeaders = {},
        encoders: Sequence[WebAPIEncoder] = [],
        encoder_kwargs: Dict[str, Any] = {},
        message_data_mimetype: Optional[str] = None,
        supported_mimetypes: Optional[List[str]] = None,
    ) -> None:
        """Initialize the API event stream.

        The provided API event stream source will be processed when sending
        content to the client, and not before.

        Args:
            event_stream (callable or generator):
                The event stream as a generator or a callable yielding
                results.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            api_format (str, optional):
                An explicit format for the result payload, used to determine
                a default for :py:attr:`message_data_mimetype`.

            status (int, optional):
                The HTTP status code to send in the response.

            headers (dict, optional):
                Custom HTTP headers to include in the response.

            encoders (list of djblets.webapi.encoders.WebAPIEncoder, optional):
                The list of encoders available to encode object payloads.

                If not provided, all registered encoders will be tried. See
                :py:func:`~djblets.webapi.encoders.get_registered_encoders`.

            encoder_kwargs (dict, optional):
                Keyword arguments to pass when instantiating encoders.

            message_data_mimetype (str, optional):
                The mimetype for the standard message data payloads.

                If not provided, one will be automatically determined based
                on ``api_format`` and the request mimetype.

            supported_mimetypes (list of str, optional):
                A list of supported mimetypes for this response.

                This is used when trying to guess a mimetype from the
                :mailheader:`Accept` header.
        """
        if not encoders:
            encoders = get_registered_encoders()

        message_data_mimetype = _normalize_response_mimetype(
            request=request,
            mimetype=message_data_mimetype,
            api_format=api_format,
            supported_mimetypes=(supported_mimetypes or
                                 WebAPIResponse.supported_mimetypes))

        def _gen_events(
            last_id: Optional[str],
        ) -> EventStreamMessages:
            nonlocal event_stream

            if callable(event_stream):
                event_stream = event_stream(last_id)

            for event in event_stream:
                if 'data' in event:
                    data = event['data']
                else:
                    data = (
                        WebAPIResponse(request,
                                       obj=event.get('obj', {}),
                                       stat=event.get('stat', 'ok'),
                                       api_format=api_format,
                                       mimetype=message_data_mimetype,
                                       encoders=encoders,
                                       encoder_kwargs=encoder_kwargs)
                        .content
                    )

                yield {
                    'data': data,
                    'event': event.get('event'),
                    'id': event.get('id'),
                    'retry_ms': event.get('retry_ms')
                }

        super().__init__(_gen_events,
                         request=request,
                         status=status)

        if message_data_mimetype:
            self['X-Event-Data-Mimetype'] = message_data_mimetype

        for header, value in headers.items():
            self[header] = value


def _normalize_response_mimetype(
    *,
    request: HttpRequest,
    mimetype: Optional[str],
    api_format: Optional[str],
    supported_mimetypes: Optional[Sequence[str]],
) -> Optional[str]:
    """Normalize a mimetype for an API response.

    If an explicit mimetype is not provided, one will be computed based on:

    1. The ``api_format``, if provided as a parameter or in the request
       (checked in that order).

    2. The value in the :mailheader:`Accept` header (f allowed in
       ``supported_mimetypes``).

    Version Added:
        4.0

    Args:
        request (django.http.HttpRequest):
            The HTTP request from the client.

        mimetype (str):
            An explicit mimetype to use.

        api_format (str):
            An explicit API format to use, instead of checking the request.

        supported_mimetypes (list of str):
            A list of supported mimetypse for :mailheader:`Accept` headers.

    Returns:
        str:
        The response mimetype to use.
    """
    if not mimetype:
        if not api_format:
            if request.method == 'GET':
                api_format = request.GET.get('api_format')
            else:
                api_format = request.POST.get('api_format')

        if not api_format:
            mimetype = get_http_requested_mimetype(
                request=request,
                supported_mimetypes=supported_mimetypes)
        elif api_format == 'json':
            mimetype = 'application/json'
        elif api_format == 'xml':
            mimetype = 'application/xml'

    return mimetype
