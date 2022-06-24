"""Storage for static media built with django-pipeline.

Version Added:
    3.0
"""

from pipeline.storage import PipelineManifestStorage


class PipelineStorage(PipelineManifestStorage):
    """Storage for static media built with django-pipeline.

    This uses the ManifestStorage backend in order to add hashes to the
    filenames, but turns off strict mode so we don't need to list each piece of
    static media in the manifest file.

    Version Added:
        3.0
    """

    manifest_strict = False
    keep_intermediate_files = True
