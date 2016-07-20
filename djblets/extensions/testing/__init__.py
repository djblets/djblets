"""Extension testing support.

This provides handy imports for extension testing classes:

* :py:class:`djblets.extensions.testing.testcases.ExtensionTestCaseMixin`
"""

from __future__ import unicode_literals

from djblets.extensions.testing.testcases import ExtensionTestCaseMixin


__all__ = [
    'ExtensionTestCaseMixin',
]

__autodoc_excludes__ = __all__
