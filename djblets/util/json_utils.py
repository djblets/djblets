from __future__ import unicode_literals

from django.utils import six


class JSONPatchError(Exception):
    """An error occurred while patching an object."""


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
