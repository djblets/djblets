"""Token generators for creating access tokens.

Version Added:
    3.0
"""

from djblets.registries.importer import lazy_import_registry


token_generator_registry = \
    lazy_import_registry('djblets.secrets.token_generators.registry',
                         'TokenGeneratorRegistry')
