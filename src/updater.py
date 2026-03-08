"""版本更新检查模块"""

import json
import time
import urllib.request
from pathlib import Path
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


def check_update_with_cache(force: bool = False, cache_hours: int = 24) -> Tuple[bool, Optional[str], Optional[str]]:
    """检查更新（带缓存）

    Args:
        force: 强制检查，忽略缓存
        cache_hours: 缓存有效期（小时）

    Returns:
        (has_update, latest_version, download_url)
    """
    cache_dir = Path.home() / ".ifly2code"
    cache_file = cache_dir / "update_cache.json"

    # 如果不是强制检查，尝试读取缓存
    if not force and cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            last_check = cache_data.get("last_check_time", 0)
            current_time = time.time()

            # 检查缓存是否过期
            if current_time - last_check < cache_hours * 3600:
                return (
                    cache_data.get("has_update", False),
                    cache_data.get("latest_version"),
                    cache_data.get("download_url")
                )
        except Exception:
            pass  # 缓存读取失败，继续检查

    # 执行实际检查
    has_update, latest_version, download_url = check_update()

    # 保存到缓存
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "last_check_time": time.time(),
            "has_update": has_update,
            "latest_version": latest_version,
            "download_url": download_url
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 缓存保存失败不影响返回结果

    return has_update, latest_version, download_url


def _version_newer(remote: str, local: str) -> bool:
    """比较版本号，remote > local 返回 True"""
    try:
        r = [int(x) for x in remote.split(".")]
        l = [int(x) for x in local.split(".")]
        return r > l
    except ValueError:
        return False
