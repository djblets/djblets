"""Compatibility imports for older extensions."""

from djblets.extensions.extension import Extension, ExtensionInfo
from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint
from djblets.extensions.manager import ExtensionManager
from djblets.extensions.settings import ExtensionSettings, Settings


__all__ = [
    'Extension', 'ExtensionHook', 'ExtensionHookPoint', 'ExtensionInfo',
    'ExtensionManager', 'ExtensionSettings', 'Settings',
]
