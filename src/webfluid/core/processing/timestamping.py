from selectolax.lexbor import LexborHTMLParser


def timestamped(path, ts):
    return path + f"?t={ts}"


def timestamped_node(src, ts):
    node = LexborHTMLParser(src, True).root
    if not node: raise ValueError("Invalid HTML source.")

    if "src" in node.attributes:
        node.attrs["src"] = timestamped(node.attrs["src"], ts)

    elif "href" in node.attributes:
        node.attrs["href"] = timestamped(node.attrs["href"], ts)

    return node
