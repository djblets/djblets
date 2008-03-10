class WebAPIError:
    """
    An API error, containing an error code and human readable message.
    """
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg


#
# Standard error messages
#
NO_ERROR                  = WebAPIError(0,   "If you see this, yell at " +
                                             "the developers")

DOES_NOT_EXIST            = WebAPIError(100, "Object does not exist")
PERMISSION_DENIED         = WebAPIError(101, "You don't have permission " +
                                             "for this")
INVALID_ATTRIBUTE         = WebAPIError(102, "Invalid attribute")
NOT_LOGGED_IN             = WebAPIError(103, "You are not logged in")
LOGIN_FAILED              = WebAPIError(104, "The username or password was " +
                                             "not correct")
INVALID_FORM_DATA         = WebAPIError(105, "One or more fields had errors")
MISSING_ATTRIBUTE         = WebAPIError(106, "Missing value for the attribute")
