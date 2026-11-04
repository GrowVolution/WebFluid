import os, sys, time

from webfluid.utils.core import parse_config, read_config


def console_encoding():
    return getattr(sys.stdout, "encoding", None) or "utf-8"


def env_from_config(config_file, debug):
    env = os.environ.copy()
    cfg = read_config(config_file)

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


def read_key(timeout=None):
    if os.name == "nt":
        import msvcrt
        deadline = None if timeout is None else time.monotonic() + timeout
        while not msvcrt.kbhit():
            if deadline is not None and time.monotonic() >= deadline: return None
            time.sleep(0.02)

        c = msvcrt.getch()
        if c in (b"\x00", b"\xe0"): msvcrt.getch()
        return c.decode(errors="replace")

    import select, termios, tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)
        if not select.select([fd], [], [], timeout)[0]: return None
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    return key
