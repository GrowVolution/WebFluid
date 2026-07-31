from .main import text, confirm, select, fixed_choice

host = text(
    "Enter the host address:",
    default="127.0.0.1"
)

port = text(
    "Enter the port number: ",
    default="8000",
    validate=lambda x: x.isdigit()
)

debug_mode = confirm(
    "Run in debug mode?     ",
    default=False
)

menu = select(
    "What do you want to do:",
    choices=[
        fixed_choice("🔄  Restart", 0),
        fixed_choice("⏹  Stop", 1),
        fixed_choice("▶  Start (if stopped)", 2),

        fixed_choice("📜  Join log (console)", 3),
        fixed_choice("🗑  Clear log folder", 4),

        fixed_choice("🧹  Clear console", 5),

        fixed_choice("🚪  Exit", 6)
    ]
)
