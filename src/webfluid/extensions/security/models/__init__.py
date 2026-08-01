
__all__ = [
    "User", "Identity",
    "Role", "Permission",
    "TOTPSecret", "WebAuthnCredential", "BackupCode",

    "ExpiredToken"
]


def __getattr__(name):
    if name in {
        "User", "Identity",
        "Role", "Permission",
        "TOTPSecret", "WebAuthnCredential", "BackupCode"
    }:
        from . import user
        return getattr(user, name)

    if name == "ExpiredToken":
        from .token import ExpiredToken
        return ExpiredToken

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
