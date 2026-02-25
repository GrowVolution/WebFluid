
class FrameworkException(Exception): pass
class EventHookException(RuntimeError, FrameworkException): pass

class NodeError(FrameworkException): pass
class TailwindError(FrameworkException): pass

class AdditiveException(FrameworkException): pass
class ManifestError(AdditiveException): pass
