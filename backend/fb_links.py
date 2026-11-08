"""Recognize links back to the portal without making network requests."""
import html
import re
from urllib.parse import unquote, urlsplit


def own_site_link(post, site_urls):
    hosts = set()
    for value in site_urls:
        if value:
            host = urlsplit(value if "://" in value else "https://" + value).hostname
            if host:
                hosts.add(host.lower().removeprefix("www.").rstrip("."))

    def contains(value):
        if isinstance(value, dict):
            return any(contains(v) for k, v in value.items() if k != "photoURL")
        if isinstance(value, list):
            return any(contains(v) for v in value)
        if not isinstance(value, str):
            return False
        # Facebook redirect links can contain a percent-encoded destination.
        for _ in range(3):
            decoded = html.unescape(unquote(value))
            if decoded == value:
                break
            value = decoded
        for match in re.finditer(r"(?=(https?://[^\s<>\"']+|(?<![\w@./-])(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/[^\s<>\"']*)?))", value, re.I):
            url = match.group(1).rstrip(".,;!?)")
            try:
                host = urlsplit(url if "://" in url else "https://" + url).hostname
            except ValueError:
                continue
            if host and host.lower().removeprefix("www.").rstrip(".") in hosts:
                return True
        return False

    return contains(post)
