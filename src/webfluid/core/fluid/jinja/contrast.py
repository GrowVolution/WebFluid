import re

_HEX = re.compile(r"^#([0-9a-fA-F]{3,8})$")
_RGB = re.compile(r"^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)")
_LIGHT = 0.179
_READABLE = 4.5


def _channels(value):
    text = str(value or "").strip()
    found = _HEX.match(text)
    if found:
        digits = found.group(1)
        if len(digits) in (3, 4): digits = "".join(char * 2 for char in digits)
        if len(digits) not in (6, 8): return None
        return tuple(int(digits[index:index + 2], 16) / 255 for index in (0, 2, 4))
    found = _RGB.match(text)
    if found: return tuple(min(float(part), 255.0) / 255 for part in found.groups())
    return None


def _linear(channel):
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(value):
    channels = _channels(value)
    if channels is None: return None
    red, green, blue = map(_linear, channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def ratio(first, second):
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def is_light(value):
    found = luminance(value)
    return found is not None and found > _LIGHT


def contrast(value, *candidates):
    if not candidates: return value
    base = luminance(value)
    rated = [(candidate, luminance(candidate)) for candidate in candidates]
    rated = [(candidate, found) for candidate, found in rated if found is not None]
    if base is None or not rated: return candidates[0]
    for candidate, found in rated:
        if ratio(base, found) >= _READABLE: return candidate
    return max(rated, key=lambda item: ratio(base, item[1]))[0]
