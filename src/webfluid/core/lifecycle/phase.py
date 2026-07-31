from webfluid.utils.core import required_arg_count


class Phase:
    def __init__(self, name, arity=0, argument=None, reverse=False, closed_after=None):
        self.name = name
        self.arity = arity
        self.argument = argument
        self.reverse = reverse
        self.closed_after = closed_after

        self._entries = []
        self._closed = False

    def __len__(self): return len(self._entries)

    def __iter__(self):
        return iter(reversed(self._entries) if self.reverse else self._entries)

    def _arity_error(self):
        if self.arity == 0:
            return f"{self.name} must not receive non optional arguments."
        return (f"{self.name} must receive exactly {self.arity} non optional "
                f"argument{'' if self.arity == 1 else 's'}"
                f"{f' ({self.argument})' if self.argument else ''}.")

    def add(self, fn):
        if self._closed:
            raise RuntimeError(f"{self.name} cannot be added after {self.closed_after}.")

        if required_arg_count(fn) != self.arity:
            raise TypeError(self._arity_error())

        self._entries.append(fn)
        return fn

    def seal(self):
        if self.closed_after: self._closed = True
        return self
