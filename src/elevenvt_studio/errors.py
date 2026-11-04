class StudioError(Exception):
    code = "STUDIO_ERROR"
    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}

class ValidationError(StudioError): code = "INVALID_INPUT"
class PermissionDenied(StudioError): code = "PERMISSION_DENIED"
class ApprovalRequired(StudioError): code = "APPROVAL_REQUIRED"
class NotFound(StudioError): code = "NOT_FOUND"
class AdapterUnavailable(StudioError): code = "NOT_CONNECTED"
class ResourceUnavailable(StudioError): code = "RESOURCE_UNAVAILABLE"
class PostconditionFailed(StudioError): code = "POSTCONDITION_FAILED"

class Conflict(StudioError):
    code = "CONFLICT"

class UncertainSideEffect(StudioError):
    code = "UNCERTAIN_SIDE_EFFECT"
