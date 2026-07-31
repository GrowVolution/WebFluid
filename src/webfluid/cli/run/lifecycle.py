import typer, subprocess, sys, os, signal


class Lifecycle:
    def __init__(self):
        self.proc = None
        self.terminate = False

        signal.signal(signal.SIGINT, self.exit)
        signal.signal(signal.SIGTERM, self.exit)

    def exit(self, signum, _):
        typer.secho(f"Handling signal {'SIGINT' if signum == signal.SIGINT else 'SIGTERM'}, "
                    "shutting down...", fg=typer.colors.YELLOW)
        self.terminate = True

    def start(self, env, project_root, log_service):
        if self.proc and self.proc.poll() is None:
            typer.secho("Application already running.", fg=typer.colors.YELLOW)
            return

        typer.secho("Starting application...", fg=typer.colors.GREEN)
        self.proc = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=log_service.log,
            env=env,
            cwd=project_root,
            text=True,
            bufsize=1,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        )

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

    def restart(self, env, project_root, log_service):
        self.stop()
        self.start(env, project_root, log_service)

    @property
    def status(self):
        running = self.proc and self.proc.poll() is None
        status = "Running" if running else "Stopped"

        if running: return typer.style(status, fg=typer.colors.GREEN)
        return typer.style(status, fg=typer.colors.RED)
