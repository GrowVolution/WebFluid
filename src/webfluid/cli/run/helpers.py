from configparser import ConfigParser
import sys, os

from webfluid.utils.core import parse_config


def console_encoding():
    return getattr(sys.stdout, "encoding", None) or "utf-8"


def env_from_config(config_file, debug):
    env = os.environ.copy()
    cfg = ConfigParser()
    cfg.optionxform = str
    cfg.read(config_file)

    pairs = [parse_config(k, v) for k, v in cfg.defaults().items()]
    for k, v in pairs: env[k] = v

    for section in cfg.sections():
        if section == "dev" and not debug: continue
        if section == "additives": env["ENABLED_ADDITIVES"] = str(sum(
            v.lower() in ("true", "1", "yes") for v in cfg[section].values()
        ))
        pairs = [parse_config(k, v) for k, v in cfg[section].items()]
        for k, v in pairs: env[k] = v

    return env


def read_key():
    if os.name == "nt":
        import msvcrt
        c = msvcrt.getch()
        if c in (b"\x00", b"\xe0"): msvcrt.getch()
        return c.decode(errors="replace")

    import termios, tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    return key
