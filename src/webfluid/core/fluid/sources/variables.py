from selectolax.lexbor import LexborHTMLParser
from tinycss2 import parse_blocks_contents, parse_component_value_list, parse_rule_list, parse_stylesheet, serialize
from tinycss2.color4 import Color
from tinycss2.color5 import parse_color
import re

_SKIP = {"skip_comments": True, "skip_whitespace": True}
_ROOT = re.compile(r"^(?P<element>:root|html)(?:\[data-theme=(?P<quote>[\"']?)(?P<scheme>[\w-]+)(?P=quote)])?$")
_WHERE = re.compile(r"^:where\((?P<inner>.+)\)$")
_SCHEME = re.compile(r"prefers-color-scheme\s*:\s*([\w-]+)")
_SPACE = re.compile(r"\s+")

_XYZ_TO_SRGB = (
    (3.2409699419045226, -1.537383177570094, -0.4986107602930034),
    (-0.9692436362808796, 1.8759675015077202, 0.04155505740717559),
    (0.05563007969699366, -0.20397695888897652, 1.0569715142428786)
)
_D50_TO_D65 = (
    (0.955473421488075, -0.02309845494876471, 0.06325924320057072),
    (-0.0283697093338637, 1.0099953980813041, 0.021041441191917323),
    (0.012314014864481998, -0.020507649298898964, 1.330365926242124)
)

_sheets = {}


def _comma(token):
    return token.type == "literal" and token.value == ","


def _parts(tokens):
    parts, current = [], []
    for token in tokens:
        if _comma(token):
            parts.append(current)
            current = []
        else: current.append(token)
    parts.append(current)
    return parts


def _specificity(selector, scheme):
    where = _WHERE.match(selector)
    if where:
        found = [_specificity(part, scheme) for part in where["inner"].split(",")]
        return (0, 0) if any(value is not None for value in found) else None

    root = _ROOT.match(selector)
    if root is None or (root["scheme"] and root["scheme"] != scheme): return None
    return int(root["element"] == ":root") + int(bool(root["scheme"])), int(root["element"] == "html")


def _applies(media, scheme):
    schemes = _SCHEME.findall(serialize(media).lower())
    return bool(schemes) and all(found == scheme for found in schemes)


def _declarations(rules, scheme):
    for rule in rules:
        if rule.type == "qualified-rule":
            found = [_specificity(_SPACE.sub("", serialize(part)), scheme) for part in _parts(rule.prelude)]
            matched = [value for value in found if value is not None]
            if not matched: continue

            for declaration in parse_blocks_contents(rule.content, **_SKIP):
                if declaration.type == "declaration" and declaration.name.startswith("--"):
                    yield declaration.important, max(matched), declaration.name, declaration.value

        elif rule.type == "at-rule" and rule.content is not None:
            nested = rule.lower_at_keyword == "layer" or (
                rule.lower_at_keyword == "media" and _applies(rule.prelude, scheme)
            )
            if nested: yield from _declarations(parse_rule_list(rule.content, **_SKIP), scheme)


def _rules(path):
    stamp = path.stat().st_mtime_ns
    cached = _sheets.get(path)
    if cached is None or cached[0] != stamp:
        cached = stamp, parse_stylesheet(path.read_text(encoding="utf-8"), **_SKIP)
        _sheets[path] = cached
    return cached[1]


def _multiply(matrix, vector):
    return tuple(sum(weight * value for weight, value in zip(row, vector)) for row in matrix)


def _encode(channel):
    channel = max(0.0, min(1.0, channel))
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055


def _srgb(colour):
    if colour.space in ("hsl", "hwb"): colour = colour.to("srgb")
    coordinates = tuple(value or 0.0 for value in colour.coordinates)

    if colour.space == "srgb": return *coordinates, colour.alpha
    if colour.space == "srgb-linear": return *(_encode(value) for value in coordinates), colour.alpha

    if colour.space in ("lab", "lch", "xyz-d50"):
        d50 = coordinates if colour.space == "xyz-d50" else colour.to("xyz-d50").coordinates
        xyz = _multiply(_D50_TO_D65, d50)
    elif colour.space in ("oklab", "oklch", "xyz-d65", "xyz"):
        xyz = coordinates if colour.space in ("xyz-d65", "xyz") else colour.to("xyz-d65").coordinates
    else: return None

    return *(_encode(value) for value in _multiply(_XYZ_TO_SRGB, xyz)), colour.alpha


def _mix(arguments, scheme):
    parts = [[token for token in part if token.type not in ("whitespace", "comment")] for part in _parts(arguments)]
    if len(parts) != 3 or not parts[0] or getattr(parts[0][0], "lower_value", None) != "in": return None

    found = []
    for part in parts[1:]:
        weights = [token.value / 100 for token in part if token.type == "percentage"]
        colours = [token for token in part if token.type != "percentage"]
        if len(colours) != 1 or len(weights) > 1: return None

        rgba = _rgba(colours[0], scheme)
        if rgba is None: return None
        found.append((rgba, weights[0] if weights else None))

    (first, share), (second, rest) = found
    if share is None and rest is None: share = rest = 0.5
    elif share is None: share = 1 - rest
    elif rest is None: rest = 1 - share

    total = share + rest
    if total <= 0: return None

    share, rest = share / total, rest / total
    alpha = first[3] * share + second[3] * rest
    if alpha == 0: return 0.0, 0.0, 0.0, 0.0

    channels = ((first[i] * first[3] * share + second[i] * second[3] * rest) / alpha for i in range(3))
    return *channels, alpha * min(total, 1.0)


def _rgba(token, scheme):
    if token.type == "function" and token.lower_name == "color-mix": return _mix(token.arguments, scheme)
    colour = parse_color(token, (scheme,) if scheme else None)
    return _srgb(colour) if isinstance(colour, Color) else None


def _format(rgba):
    red, green, blue = (round(max(0.0, min(1.0, value)) * 255) for value in rgba[:3])
    alpha = round(max(0.0, min(1.0, rgba[3])), 3)
    if alpha >= 1: return f"#{red:02x}{green:02x}{blue:02x}"
    return f"rgba({red}, {green}, {blue}, {alpha:g})"


def _token(token, scheme):
    if token.type in ("hash", "function"):
        rgba = _rgba(token, scheme)
        if rgba is not None: return _format(rgba)

    if token.type == "function":
        return f"{token.name}({''.join(_token(child, scheme) for child in token.arguments)})"
    return serialize([token])


def _concrete(value, scheme):
    tokens = parse_component_value_list(value, skip_comments=True)
    significant = [token for token in tokens if token.type != "whitespace"]

    if len(significant) == 1 and significant[0].type == "ident":
        rgba = _rgba(significant[0], scheme)
        return value if rgba is None else _format(rgba)

    return "".join(_token(token, scheme) for token in tokens).strip()


class _Resolver:
    def __init__(self, raw):
        self.raw = raw
        self.done = {}
        self.active = set()

    def _var(self, arguments):
        cut = next((index for index, token in enumerate(arguments) if _comma(token)), None)
        names = [token for token in (arguments if cut is None else arguments[:cut]) if token.type == "ident"]

        value = self.value(names[0].value) if names else None
        if value is not None: return value
        return None if cut is None else self.tokens(arguments[cut + 1:])

    def tokens(self, tokens):
        parts = []
        for token in tokens:
            if token.type != "function":
                parts.append(serialize([token]))
                continue

            var = token.lower_name == "var"
            inner = self._var(token.arguments) if var else self.tokens(token.arguments)
            if inner is None: return None
            parts.append(inner if var else f"{token.name}({inner})")
        return "".join(parts)

    def value(self, name):
        if name in self.done: return self.done[name]
        if name in self.active or name not in self.raw: return None

        self.active.add(name)
        value = self.tokens(self.raw[name])
        self.active.discard(name)

        self.done[name] = None if value is None else value.strip()
        return self.done[name]


def stylesheets(markup):
    found = []
    for node in LexborHTMLParser(str(markup)).css("link"):
        rel = (node.attributes.get("rel") or "").lower().split()
        href = node.attributes.get("href")
        if "stylesheet" in rel and href: found.append(href)
    return found


def variables(paths, scheme=None):
    entries = [entry for path in paths for entry in _declarations(_rules(path), scheme)]
    order = sorted(range(len(entries)), key=lambda index: (entries[index][0], entries[index][1], index))

    raw = {}
    for index in order:
        raw[entries[index][2]] = entries[index][3]

    resolver = _Resolver(raw)
    resolved = {}
    for name in raw:
        value = resolver.value(name)
        if value: resolved[name] = _concrete(value, scheme)
    return resolved
