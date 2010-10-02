class EnablingExtensionError(Exception):
    """An error indicating that an extension could not be enabled"""
    pass


class DisablingExtensionError(Exception):
    """An error indicating that an extension could not be disabled"""
    pass


class InstallExtensionError(Exception):
    """An error indicating that an extension could not be installed"""
    pass


class InvalidExtensionError(Exception):
    """An error indicating that an extension does not exist"""
    def __init__(self, extension_id):
        super(InvalidExtensionError, self).__init__()
        self.message = "Cannot find extension with id %s" % extension_id
