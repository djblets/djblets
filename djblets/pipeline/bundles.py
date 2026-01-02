"""Definitions for Pipeline bundles.

Version Added:
    5.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any, Literal

    from typing_extensions import NotRequired


class StaticBundle(TypedDict):
    """Definition for a static bundle.

    This corresponds to the group options listed at
    https://django-pipeline.readthedocs.io/en/latest/configuration.html#group-options

    Version Added:
        5.3
    """

    #: The filename to use for the compiled bundle.
    output_filename: str

    #: The list of entry-point files that should be included in the bundle.
    source_filenames: Sequence[str]

    #: The variant to apply to CSS.
    variant: NotRequired[Literal['datauri'] | None]

    #: A dictionary passed to the compiler's ``compile_file`` method.
    compiler_options: NotRequired[Mapping[str, Any]]

    #: Extra context to use when rendering the template.
    extra_context: NotRequired[Mapping[str, Any]]

    #: Whether to include the bundle in the cache manifest.
    manifest: NotRequired[bool]

    #: The name of the template used to render the HTML tags.
    template_name: NotRequired[str]
