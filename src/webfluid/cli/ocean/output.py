from typing import Optional


def truncate(text: str, width: int) -> str:
    text = text.replace("\n", " ")
    if width <= 0 or len(text) <= width: return text
    if width == 1: return "…"
    return text[:width - 1] + "…"


def render_table(headers: list[str], rows: list[list[str]],
                 max_widths: Optional[list[int]] = None) -> str:
    cols = len(headers)
    max_widths = max_widths or [0] * cols

    widths = []
    for i in range(cols):
        longest = max(
            [len(str(row[i])) for row in rows] + [len(headers[i])]
        )
        cap = max_widths[i]
        widths.append(min(longest, cap) if cap else longest)

    def line(cells: list) -> str:
        return " | ".join(
            truncate(str(cell), widths[i]).ljust(widths[i])
            for i, cell in enumerate(cells)
        )

    divider = "-+-".join("-" * width for width in widths)
    return "\n".join([line(headers), divider] + [line(row) for row in rows])


def package_state(item: dict) -> str:
    if item.get("oss"): return "OSS"
    if item.get("owned"): return "owned"
    price = item.get("price")
    return f"€{price:.2f}" if price is not None else "—"
