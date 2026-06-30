
class FrameworkException(Exception): pass

class FrontendException(FrameworkException): pass
class NodeError(FrontendException): pass
class TailwindError(FrontendException): pass

class AdditiveException(FrameworkException): pass
class ManifestError(AdditiveException): pass

class OceanError(FrameworkException):
    def __init__(self, status, detail):
        self.status = status
        self.detail = detail
        super().__init__(detail if not status else f"[{status}] {detail}")
