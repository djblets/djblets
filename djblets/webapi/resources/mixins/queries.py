"""Mixins for helping with lookups from HTTP GET query strings."""

from __future__ import unicode_literals

from django.db.models import Q


class APIQueryUtilsMixin(object):
    """Adds useful functions to a WebAPIResource for database lookups."""

    def build_queries_for_int_field(self, request, field_name,
                                    query_param_name=None):
        """Build queries based on request parameters for an int field.

        :py:meth:`get_queryset` implementations can use this to allow callers
        to filter results through range matches. Callers can search for exact
        matches, or can make use of the following operations:

        * ``<`` (:samp:`?{name}-lt={value}`)
        * ``<=`` (:samp:`?{name}-lte={value}`)
        * ``>`` (:samp:`?{name}-gt={value}`)
        * ``>=`` (:samp:`?{name}-gte={value}`)

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            field_name (unicode):
                The field name in the database to query against.

            query_param_name (unicode):
                The query argument passed to the URL. Defaults to the
                ``field_name``.

        Returns:
            django.db.models.Q:
            A query expression that can be used in database queries.
        """
        if not query_param_name:
            query_param_name = field_name.replace('_', '-')

        q = Q()

        if query_param_name in request.GET:
            q = q & Q(**{field_name: request.GET[query_param_name]})

        for op in ('gt', 'gte', 'lt', 'lte'):
            param = '%s-%s' % (query_param_name, op)

            if param in request.GET:
                query_field = '%s__%s' % (field_name, op)

                try:
                    q = q & Q(**{query_field: int(request.GET[param])})
                except ValueError:
                    # Not a valid query, so ignore it.
                    pass

        return q
