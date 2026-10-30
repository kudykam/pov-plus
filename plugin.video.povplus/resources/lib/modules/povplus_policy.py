# Modified for POV+ by kudykam · 2026-10-30 · GPL-3.0-only
"""POV+ release policy. Pure functions: no Kodi/network side effects."""
import math
import re

_VERSION = 1
_BAD_QUALITY = {'CAM', 'TELE', 'TS', 'TC', 'SCR', 'SCREENER', 'HDCAM', 'HDTS', 'HDTC'}
_BAD = re.compile(r'(?:^|[\W_])(?:camrip|hdcam|hqcam|dvdcam|telesync|telecine|hdts|hdtc|tsrip|dvdscr|screener|cam|ts|tc|scr|r5|r6)(?:$|[\W_])', re.I)
_HIGH_BAD = re.compile(r'(?:^|[\W_])(?:camrip|hdcam|hqcam|dvdcam|telesync|telecine|hdts|hdtc|tsrip|dvdscr|screener)(?:$|[\W_])', re.I)
_RES = [(2160, re.compile(r'(?:^|[\W_])(?:2160p?|4k|uhd)(?:$|[\W_])', re.I)),
        (1080, re.compile(r'(?:^|[\W_])1080[pi]?(?:$|[\W_])', re.I)),
        (720, re.compile(r'(?:^|[\W_])720[pi]?(?:$|[\W_])', re.I))]


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def release_name(item):
    return str(item.get('name') or item.get('release_title') or item.get('filename') or item.get('title') or '')


def prerelease(item):
    if str(item.get('quality', '')).upper() in _BAD_QUALITY:
        return True
    name = release_name(item)
    # A film called "Cam (2018)" is not a camera rip. Generic tokens before
    # the release year belong to the title; explicit HDCAM/TELESYNC still win.
    year = re.search(r'(?<!\d)(?:19|20)\d{2}(?!\d)', name)
    suffix = name[year.end():] if year else name
    return bool(_HIGH_BAD.search(name) or _BAD.search(suffix))


def resolution(item):
    name = release_name(item)
    for value, pattern in _RES:
        if pattern.search(str(item.get('quality', '')) + ' ' + name):
            return value
    return 480 if str(item.get('quality', '')).upper() == 'SD' else None


def evaluate(item, duration_seconds, minimum=1080, budget_mbps=40):
    duration, budget, size_gb = number(duration_seconds), number(budget_mbps), number(item.get('size'))
    q = resolution(item)
    mbps = size_gb * 1073741824 * 8 / 1000000 / duration if size_gb is not None and size_gb > 0 and duration is not None and duration > 0 else None
    if prerelease(item): reason = 'prerelease'
    elif q is None: reason = 'unknown_quality'
    elif q < minimum: reason = 'below_quality'
    elif mbps is None: reason = 'unknown_bitrate'
    elif budget is None or not 0 < budget <= 50: reason = 'invalid_budget'
    elif mbps > budget: reason = 'over_budget'
    else: reason = None
    return {'eligible': reason is None, 'reason': reason, 'resolution': q,
            'sizeGiB': size_gb, 'averageMbps': mbps, 'evidence': 'provider_reported'}


def best_stream(items, duration_seconds, minimum=1080, budget_mbps=40):
    results = []
    for item in items:
        summary = evaluate(item, duration_seconds, minimum, budget_mbps)
        if summary['eligible']:
            text = release_name(item) + ' ' + str(item.get('extraInfo', ''))
            summary['hdr'] = 'Dolby Vision' if re.search(r'\b(?:dovi|dolby[ ._-]?vision|dv)\b|D/VISION', text, re.I) else 'HDR' if 'HDR' in text.upper() else 'SDR'
            summary['audio'] = 'Atmos' if 'ATMOS' in text.upper() else ''
            results.append(summary)
    return max(results, key=lambda s: (s['resolution'], s['hdr'] != 'SDR', s['audio'] == 'Atmos', s['sizeGiB'])) if results else None


def strict_results(items, duration_seconds, minimum=1080, budget_mbps=40):
    return [item for item in items if evaluate(item, duration_seconds, minimum, budget_mbps)['eligible']]


def stars(percent):
    p = number(percent)
    if p is None or not 0 <= p <= 100:
        return 'ČSFD —'
    filled = min(5, max(0, int(p / 20 + 0.5)))
    return '%s%s ČSFD %s%%' % ('★' * filled, '☆' * (5 - filled), format(p, 'g'))


def meets_rating(percent, minimum):
    p, minimum = number(percent), number(minimum)
    return minimum is not None and (minimum <= 0 or (p is not None and 0 <= p <= 100 and p >= minimum))
