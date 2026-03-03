"""版本更新检查模块"""

import json
import urllib.request
from typing import Optional, Tuple

from .version import __version__

GITHUB_API = "https://api.github.com/repos/caozeze/ifly2code/releases/latest"


def check_update() -> Tuple[bool, Optional[str], Optional[str]]:
    """检查 GitHub Release 是否有新版本

    Returns:
        (has_update, latest_version, download_url)
    """
    try:
        req = urllib.request.Request(GITHUB_API, headers={"Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        tag = data.get("tag_name", "").lstrip("vV")
        if not tag:
            return False, None, None

        if _version_newer(tag, __version__):
            url = data.get("html_url", "")
            return True, tag, url

        return False, tag, None
    except Exception:
        return False, None, None


def _version_newer(remote: str, local: str) -> bool:
    """比较版本号，remote > local 返回 True"""
    try:
        r = [int(x) for x in remote.split(".")]
        l = [int(x) for x in local.split(".")]
        return r > l
    except ValueError:
        return False
