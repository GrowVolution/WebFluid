from pathlib import Path

async def manipulate_index(
    frontend_path: Path, relative_path: str, framework: str, html_str: str
) -> str: ...
