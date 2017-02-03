import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.utils.encoding import force_text
from django.utils.functional import Promise


class DjbletsJSONEncoder(DjangoJSONEncoder):
    """A JSON encoder that supports lazy strings, datetimes, and some models.

    This is a specialization of
    :py:class:`~django.core.serializers.json.DjangoJSONEncoder` the does the
    following:

    * Evaluates strings translated with
      :py:meth:`~django.utils.translation.ugettext_lazy` or
      :py:meth:`~django.utils.translation.gettext_lazy` to real strings.

    * Removes the milliseconds and microseconds from
      :py:class:`datetimes <datetime.datetime>`.

    * Serializes Django :py:class:`models <django.db.models.base.Model>` with
      a ``to_json`` method via that method.
    """

    def default(self, obj):
        """Encode the object into a JSON-compatible structure.

        Args:
            obj (object):
                The object to encode.

        Returns:
            object:
            A JSON-compatible structure (e.g., a :py:class:`dict`,
            :py:class:`list`, py:class:`unicode`, or :py:class:`bytes` object).
        """
        if isinstance(obj, Promise):
            # Handles initializing lazily created ugettext messages.
            return force_text(obj)
        elif isinstance(obj, datetime.datetime):
            # This is like DjangoJSONEncoder's datetime encoding
            # implementation, except that it filters out the milliseconds
            # in addition to microseconds. This ensures consistency between
            # database-stored timestamps and serialized objects.
            r = obj.isoformat()

            if obj.microsecond:
                r = r[:19] + r[26:]

            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'

            return r
        elif (isinstance(obj, Model) and
              hasattr(obj, 'to_json') and
              callable(obj.to_json)):
            return obj.to_json()

        return super(DjbletsJSONEncoder, self).default(obj)
