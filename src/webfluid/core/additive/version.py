from webfluid.utils.core import final_version


class Version(tuple):
    def __init__(self, major, minor=None, patch=None):
        if minor is None and patch is None:
            _, self.stage, self.build = final_version(major)
        elif minor is not None and patch is None:
            _, self.stage, self.build = final_version(minor)
        elif patch is not None:
            _, self.stage, self.build = final_version(patch)
        else: raise ValueError("Invalid version format.")

    def __new__(cls, major, minor=None, patch=None):
        if minor is None and patch is None: self = (final_version(major)[0],)
        elif patch is None: self = (int(major), final_version(minor)[0])
        else: self = (int(major), int(minor), final_version(patch)[0])
        return super().__new__(cls, self)

    def __str__(self):
        return (f"{'.'.join(map(str, self))}{self.stage}"
                f"{self.build if self.stage else ''}")
