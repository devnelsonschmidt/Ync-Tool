"""
TLS Browser Impersonation via curl_cffi.
Provides JA3/JA4 fingerprint spoofing to match real Chrome/Firefox/Safari.
"""

try:
    from curl_cffi.requests import Session as CurlSession
    from curl_cffi import CurlOpt
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

CHROME_CIPHERS = ":".join([
    "TLS_AES_128_GCM_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-RSA-AES128-GCM-SHA256",
    "ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-CHACHA20-POLY1305",
    "ECDHE-RSA-CHACHA20-POLY1305",
    "ECDHE-RSA-AES128-SHA",
    "ECDHE-RSA-AES256-SHA",
    "AES128-GCM-SHA256",
    "AES256-GCM-SHA384",
    "AES128-SHA",
    "AES256-SHA",
])

CHROME_H2_SETTINGS = {
    "HEADER_TABLE_SIZE": 65536,
    "MAX_CONCURRENT_STREAMS": 1000,
    "INITIAL_WINDOW_SIZE": 6291456,
    "MAX_HEADER_LIST_SIZE": 262144,
}

FIREFOX_H2_SETTINGS = {
    "HEADER_TABLE_SIZE": 65536,
    "MAX_CONCURRENT_STREAMS": 1000,
    "INITIAL_WINDOW_SIZE": 131072,
    "MAX_HEADER_LIST_SIZE": 262144,
}

SAFARI_H2_SETTINGS = {
    "HEADER_TABLE_SIZE": 200,
    "MAX_CONCURRENT_STREAMS": 1000,
    "INITIAL_WINDOW_SIZE": 2097152,
    "MAX_HEADER_LIST_SIZE": 1048576,
}

PROFILES = {
    "chrome136": {
        "impersonate": "chrome136",
        "h2_settings": CHROME_H2_SETTINGS,
        "pseudo_header_order": ["m", "a", "s", "p"],
    },
    "chrome133": {
        "impersonate": "chrome133",
        "h2_settings": CHROME_H2_SETTINGS,
        "pseudo_header_order": ["m", "a", "s", "p"],
    },
    "chrome131": {
        "impersonate": "chrome131",
        "h2_settings": CHROME_H2_SETTINGS,
        "pseudo_header_order": ["m", "a", "s", "p"],
    },
    "chrome124": {
        "impersonate": "chrome124",
        "h2_settings": CHROME_H2_SETTINGS,
        "pseudo_header_order": ["m", "a", "s", "p"],
    },
    "chrome120": {
        "impersonate": "chrome120",
        "h2_settings": CHROME_H2_SETTINGS,
        "pseudo_header_order": ["m", "a", "s", "p"],
    },
    "firefox133": {
        "impersonate": "firefox133",
        "h2_settings": FIREFOX_H2_SETTINGS,
        "pseudo_header_order": ["m", "p", "a", "s"],
    },
    "firefox120": {
        "impersonate": "firefox120",
        "h2_settings": FIREFOX_H2_SETTINGS,
        "pseudo_header_order": ["m", "p", "a", "s"],
    },
    "safari18_0": {
        "impersonate": "safari18_0",
        "h2_settings": SAFARI_H2_SETTINGS,
        "pseudo_header_order": ["m", "s", "p", "a"],
    },
    "safari17_5": {
        "impersonate": "safari17_5",
        "h2_settings": SAFARI_H2_SETTINGS,
        "pseudo_header_order": ["m", "s", "p", "a"],
    },
    "edge131": {
        "impersonate": "edge131",
        "h2_settings": CHROME_H2_SETTINGS,
        "pseudo_header_order": ["m", "a", "s", "p"],
    },
}

PROFILE_NAMES = list(PROFILES.keys())


def create_session(profile_name=None):
    if not HAS_CURL_CFFI:
        return None
    if profile_name is None:
        import random
        profile_name = random.choice(PROFILE_NAMES)
    profile = PROFILES.get(profile_name, PROFILES["chrome136"])
    session = CurlSession(
        impersonate=profile["impersonate"],
        timeout=9,
    )
    try:
        session.curl.setopt(CurlOpt.HTTP_VERSION, 2)
    except Exception:
        pass
    return session


def send_request(session, method, url, headers=None, cookies=None,
                 body=None, timeout=9):
    if session is None:
        return None
    try:
        resp = session.request(
            method=method,
            url=url,
            headers=headers or {},
            cookies=cookies or {},
            data=body,
            timeout=timeout,
            allow_redirects=False,
        )
        return resp
    except Exception:
        return None
