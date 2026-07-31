

health_py = """from datetime import datetime, UTC


def handle_request():
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat()
    }
"""


tailwind_raw = """@import "tailwindcss" source("../../");

@theme {
    /* ... */
}"""


vite_base = """
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
})
"""
