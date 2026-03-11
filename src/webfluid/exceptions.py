
class FrameworkException(Exception): pass
class EventHookException(RuntimeError, FrameworkException): pass
class ProcessorException(EventHookException): pass

class FrontendException(FrameworkException): pass
class NodeError(FrontendException): pass
class TailwindError(FrontendException): pass

class AdditiveException(FrameworkException): pass
class ManifestError(AdditiveException): pass
