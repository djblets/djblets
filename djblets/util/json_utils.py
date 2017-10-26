from __future__ import unicode_literals

from django.utils import six
from django.utils.translation import ugettext as _


class JSONPatchError(Exception):
    """An error occurred while patching an object."""


class JSONPointerError(Exception):
    """Base class for JSON Pointer errors."""


class JSONPointerSyntaxError(JSONPointerError):
    """Syntax error in a JSON Pointer path."""


class JSONPointerLookupError(JSONPointerError):
    """Error looking up data from a JSON Pointer path."""

    def __init__(self, msg, parent, token, token_index, tokens):
        """Initialize the error.

        Args:
            msg (unicode):
                The error message.

            parent (object):
                The parent object. This may be a dictionary or a list.

            token (unicode):
                The last resolvable token in the path. This will be ``None``
                if the first token failed.

            token_index (int):
                The 0-based index of the last resolvable token in the path.
                This will be ``None`` if the first token failed.

            tokens (list of unicode):
                The list of tokens comprising the full path.
        """
        super(JSONPointerLookupError, self).__init__(msg)

        self.parent = parent
        self.token = token
        self.token_index = token_index
        self.tokens = tokens


class JSONPointerEndOfList(object):
    """A representation of the end of a list.

    This is used by the JSON Pointer functions to represent the very end of
    a list (not the last item). This is used primarily when specifying an
    insertion point, with this value repersenting appending to a list.
    """

    def __init__(self, json_list):
        """Initialize the object.

        Args:
            json_list (list):
                The list this object represents.
        """
        self.json_list = json_list

    def __eq__(self, other_list):
        """Return whether two instances are equal.

        Instances are equal if both of their lists are equal.

        Args:
            other_list (JSONPointerEndOfList):
                The other instance to compare to for equality.

        Returns:
            bool:
            ``True`` if the two lists are equal.
        """
        return self.json_list == other_list.json_list

    def __repr__(self):
        """Return a string representation of the instance.

        Returns:
            unicode:
            A string representation of the instance.
        """
        return 'JSONPointerEndOfList<%r>' % self.json_list


def json_merge_patch(doc, patch, can_write_key_func=None):
    """Apply a JSON Merge Patch to a value.

    This is an implementation of the proposed JSON Merge Patch standard
    (:rfc:`7396`), which is a simple algorithm for applying changes to a
    JSON-compatible data structure.

    This will attempt to merge the contents of the ``patch`` object into the
    ``doc`` object as best as possible, using the following rules:

    * If a key in ``patch`` matches a key in ``doc``, and the value is
      ``None``, the key in ``doc`` is removed.

    * If a key in ``patch`` matches a key in ``doc``, and the value is a
      dictionary, this method will be called on the values in each and the
      result will be stored as the new value.

    * If a key in ``patch`` matches a key in ``doc``, and the value is not a
      dictionary, the value from ``patch`` will replace the value in
      ``doc``.

    * If ``patch`` is a dictionary but ``doc`` is not, then ``patch`` will
      be returned directly.

    * If ``patch`` is a dictionary but ``doc`` is not, then ``doc`` will
      be discarded and the JSON Merge Patch will be applied to a new empty
      dictionary.

    * If ``patch`` is not a dictionary, then ``patch`` will be returned
      directly.

    Args:
        doc (object):
            The JSON-compatible document object the patch is being applied to.
            This will usually be a :js:class:`dict`.

        patch (object):
            The JSON-compatible patch to apply.

        can_write_key_func (callable, optional):
            An optional function to call for each key to determine if the
            key can be written in the new dictionary. This must take the
            following form:

            .. code-block:: python

               def can_write_key(doc, patch, path, **kwargs):
                   ...

            This must return a boolean indicating if the key can be written, or
            may raise a :py:class:`JSONPatchError` to abort the patching
            process. If the function returns ``False``, the key will simply be
            skipped.

    Returns:
        object:
        The resulting object. This will be the same type as ``patch``.

    Raises:
        JSONPatchError:
            There was an error patching the document. This is only raised by
            ``can_write_key_func`` implementations.

        ValueError:
            A provided parameter was incorrect.
    """
    def _merge_patch(cur_doc, cur_patch, parent_path=()):
        if isinstance(cur_patch, dict):
            if isinstance(cur_doc, dict):
                new_doc = cur_doc.copy()
            else:
                # Override the contents of the doc with a new, empty
                # dictionary, which will then be populated.
                new_doc = {}

            for key, value in six.iteritems(cur_patch):
                path = parent_path + (key,)

                if (can_write_key_func and
                    not can_write_key_func(doc=doc,
                                           patch=patch,
                                           path=path)):
                    # We can't write this key. We'll skip it, since the
                    # function didn't raise an exception.
                    continue

                if value is None:
                    new_doc.pop(key, None)
                else:
                    new_doc[key] = _merge_patch(new_doc.get(key), value, path)

            return new_doc
        else:
            return cur_patch

    if can_write_key_func and not callable(can_write_key_func):
        raise ValueError('can_write_key_func must be callable')

    return _merge_patch(doc, patch)


def json_get_pointer_info(obj, path):
    """Return information from a JSON object based on a JSON Pointer path.

    JSON Pointers are a standard way of specifying a path to data within a
    JSON object. This method takes a JSON Pointer path and returns information
    from the given object based on that path.

    Pointer paths consist of dictionary keys, array indexes, or a special ``-``
    token (representing the end of a list, after the last item) separated by
    ``/`` tokens. There are also two special escaped values: ``~0``,
    representing a ``~`` character, and ``~1``, representing a ``/`` character.

    Paths must start with ``/``, or must be an empty string (which will match
    the provided object). If the path has a trailing ``/``, then the final
    token is actually an empty string (matching an empty key in a dictionary).

    If the Pointer does not resolve to a complete path (for instance, a key
    specified in the path is missing), the resulting information will return
    the keys that could be resolved, keys that could not be resolved, the
    object where it left off, and an error message. This allows implementations
    to determine which part of a path does not yet exist, potentially for the
    purpose of inserting data at that key in the path.

    Args:
        obj (object or list):
            The object or list representing the starting object for the path.

        path (unicode):
            The Pointer path for the lookup.

    Returns:
        dict:
        Information about the object and what the path was able to match. This
        has the following keys:

        ``value`` (:py:class:`object`):
            The resulting value from the path, if the path was fully resolved.

            This will be a :py:class:`JSONPointerEndOfList` if the last part of
            the path was a ``-`` token (representing the very end of
            a list).

        ``tokens`` (:py:class:`list`):
            The normalized (unescaped) list of path tokens that comprise the
            full path.

        ``parent`` (:py:class:`object`):
            The parent object for either the most-recently resolved value.

        ``resolved`` (:py:class:`list`):
            The list of resolved objects from the original JSON object. This
            will contain each key, array item, or other value that was found,
            in path order.

        ``lookup_error`` (:py:class:`unicode`):
            The error message, if any, if failing to resolve the full path.

    Raises:
        JSONPointerSyntaxError:
            There was a syntax error with a token in the path.
    """
    if path != '' and not path.startswith('/'):
        raise JSONPointerSyntaxError(
            _('Paths must either be empty or start with a "/"'))

    # Split the path into segments, trimming off the first entry (the root
    # object). If path is empty, the split will be a no-op, and we'll end up
    # operating on the root object itself.
    tokens = path.split('/')[1:]

    # Decode the special values for "/" and "~". The decode order here is
    # important.
    norm_tokens = [
        token.replace('~1', '/').replace('~0', '~')
        for token in tokens
    ]

    resolved = [obj]
    lookup_error = None
    parent = None

    for i, token in enumerate(norm_tokens):
        parent = obj

        if isinstance(obj, dict):
            try:
                obj = obj[token]
            except KeyError:
                lookup_error = (
                    _('Dictionary key "%(key)s" not found in "%(path)s"')
                    % {
                        'key': token,
                        'path': '/%s' % '/'.join(tokens[:i]),
                    }
                )
        elif isinstance(obj, list):
            if token == '-':
                obj = JSONPointerEndOfList(obj)
            else:
                if token != '0' and token.startswith('0'):
                    raise JSONPointerSyntaxError(
                        _('List index "%s" must not begin with "0"') % token)

                try:
                    token = int(token)
                except ValueError:
                    raise JSONPointerSyntaxError(
                        _('%(index)r is not a valid list index in "%(path)s"')
                        % {
                            'index': token,
                            'path': '/%s' % '/'.join(tokens[:i]),
                        })

                if token < 0:
                    raise JSONPointerSyntaxError(
                        _('Negative indexes into lists are not allowed'))

                try:
                    obj = obj[token]
                except IndexError:
                    lookup_error = (
                        _('%(index)d is outside the list in "%(path)s"')
                        % {
                            'index': token,
                            'path': '/%s' % '/'.join(tokens[:i]),
                        }
                    )
        else:
            lookup_error = (
                _('Cannot resolve path within unsupported type "%(type)s" at '
                  '"%(path)s"')
                % {
                    'type': type(obj).__name__,
                    'path': '/%s' % '/'.join(tokens[:i]),
                }
            )

        if lookup_error:
            obj = None
            break

        resolved.append(obj)

    return {
        'value': obj,
        'parent': parent,
        'all_tokens': norm_tokens,
        'resolved_values': resolved,
        'resolved_tokens': norm_tokens[:len(resolved) - 1],
        'unresolved_tokens': norm_tokens[len(resolved) - 1:],
        'lookup_error': lookup_error,
    }


def json_resolve_pointer(obj, path):
    """Return the value from a JSON object based on a JSON Pointer path.

    See :py:func:`json_get_pointer_info` for information on how a Pointer
    path is constructed. Unlike that function, this requires a fully-resolved
    path.

    Args:
        obj (object or list):
            The object or list representing the starting object for the path.

        path (unicode):
            The Pointer path for the lookup.

    Returns:
        object:
        The resulting value from the object, based on the path.

        This will be a :py:class:`JSONPointerEndOfList` if the last part of
        the path was a ``-`` token (representing the very end of
        a list).

    Raises:
        JSONPointerLookupError:
            The path could not be fully resolved.

        JSONPointerSyntaxError:
            There was a syntax error with a token in the path.
    """
    info = json_get_pointer_info(obj, path)
    lookup_error = info['lookup_error']

    if lookup_error:
        tokens = info['all_tokens']
        parent = info['parent']

        if parent is None:
            token_index = None
            token = None
        else:
            token_index = len(info['resolved_tokens']) - 1
            token = tokens[token_index]

        raise JSONPointerLookupError(lookup_error,
                                     parent=parent,
                                     token=token,
                                     token_index=token_index,
                                     tokens=tokens)

    return info['value']
