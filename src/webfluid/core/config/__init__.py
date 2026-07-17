

__all__ = [
    "Config", "DefaultConfig",

    "register_config"
]


def __getattr__(name):
    if name == "Config":
        from .main import Config
        return Config

    if name == "DefaultConfig":
        from .default import DefaultConfig
        return DefaultConfig

    if name == "register_config":
        from .register import register_config
        return register_config

    raise AttributeError(name)
