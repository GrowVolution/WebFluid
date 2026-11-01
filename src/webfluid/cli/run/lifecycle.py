import os, signal, subprocess, sys, typer


def _require_log_service(fn):
    def wrapper(self, *args, **kwargs):
        if self._log_service is None:
            raise RuntimeError("LogService has not been attached.")
        return fn(self, *args, **kwargs)
    return wrapper


class Lifecycle:
    def __init__(self, env, project_root):
        self._env = env
        self._project_root = project_root
        self._log_service = None

        self.proc = None
        self.terminate = False

        signal.signal(signal.SIGINT, self.exit)
        signal.signal(signal.SIGTERM, self.exit)

    def attach_log_service(self, log_service):
        if self._log_service is not None:
            raise RuntimeError("LogService has already been attached.")
        self._log_service = log_service

    def exit(self, signum, _):
        typer.secho(f"Handling signal {'SIGINT' if signum == signal.SIGINT else 'SIGTERM'}, "
                    "shutting down...", fg=typer.colors.YELLOW)
        self.terminate = True

    def restart(self): self.stop(); self.start()

    @_require_log_service
    def start(self):
        if self.proc and self.proc.poll() is None:
            typer.secho("Application already running.", fg=typer.colors.YELLOW)
            return

        typer.secho("Starting application...", fg=typer.colors.GREEN)
        self.proc = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=self._log_service.log,
            env=self._env,
            cwd=self._project_root,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        )

    @_require_log_service
    def stop(self):
        if self.proc is None:
            typer.secho("Application not running.", fg=typer.colors.YELLOW)
            return

        if self.proc.poll() is None:
            typer.secho("Stopping application...", fg=typer.colors.RED)
            if os.name == "nt":
                os.kill(self.proc.pid, signal.CTRL_BREAK_EVENT)
            else:
                self.proc.send_signal(signal.SIGTERM)

            try: self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()

            self.proc = None

    @property
    def status(self):
        running = self.proc and self.proc.poll() is None
        status = "Running" if running else "Stopped"

        if running: return typer.style(status, fg=typer.colors.GREEN)
        return typer.style(status, fg=typer.colors.RED)
