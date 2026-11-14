# -*- coding: utf-8 -*-
"""元宝搜索 SearchPro API 客户端（零第三方依赖，纯标准库 TC3-HMAC-SHA256 签名）

接口坐标（钉死，别改）：
    HOST    wsa.tencentcloudapi.com
    SERVICE wsa
    VERSION 2025-05-08
    ACTION  SearchPro

用法：
    from wsa_client import WsaClient
    c = WsaClient()                      # 自动读同目录 .env，或环境变量
    c.search("腾讯股价", mode=1)          # 原始返回
    c.pages("G677", mode=1, cnt=10)      # 解析后的 Pages 列表

密钥来源优先级：显式入参 > 同目录 .env > 进程环境变量。
"""
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

HOST = "wsa.tencentcloudapi.com"
SERVICE = "wsa"
VERSION = "2025-05-08"
ACTION = "SearchPro"


def _load_env(env_path: Path) -> dict:
    out = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_dotenv(env_path: str | Path) -> bool:
    """把 .env 读进进程环境变量（供 WsaClient 无参构造时兜底）。"""
    p = Path(env_path)
    env = _load_env(p)
    if not env:
        return False
    for k, v in env.items():
        os.environ.setdefault(k, v)
    return True


class WsaClient:
    def __init__(self, secret_id: str = "", secret_key: str = "", env_file: str | None = None):
        search_paths = []
        if env_file:
            search_paths.append(Path(env_file))
        search_paths.append(Path(__file__).parent / ".env")
        search_paths.append(Path.cwd() / ".env")
        env = {}
        for p in search_paths:
            env.update(_load_env(p))
        self.secret_id = secret_id or env.get("TENCENTCLOUD_SECRET_ID") or os.environ.get("TENCENTCLOUD_SECRET_ID", "")
        self.secret_key = secret_key or env.get("TENCENTCLOUD_SECRET_KEY") or os.environ.get("TENCENTCLOUD_SECRET_KEY", "")
        if not self.secret_id or not self.secret_key:
            raise ValueError(
                "缺少腾讯云密钥。请设置 TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY：\n"
                "  方式一：在项目目录建 .env（两行，见 templates/.env.example）\n"
                "  方式二：导出环境变量"
            )
        self.calls = 0   # 便于成本核算

    # ---------- TC3-HMAC-SHA256 签名（严格按腾讯云文档，勿动） ----------
    def _sign(self, timestamp: int, payload: bytes) -> str:
        date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))

        canonical_request = "\n".join([
            "POST",
            "/",
            "",
            f"content-type:application/json; charset=utf-8\nhost:{HOST}\nx-tc-action:{ACTION.lower()}\n",
            "content-type;host;x-tc-action",
            hashlib.sha256(payload).hexdigest(),
        ])

        string_to_sign = "\n".join([
            "TC3-HMAC-SHA256",
            str(timestamp),
            f"{date}/{SERVICE}/tc3_request",
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ])

        k_date = hmac.new(("TC3" + self.secret_key).encode("utf-8"), date.encode("utf-8"), hashlib.sha256).digest()
        k_service = hmac.new(k_date, SERVICE.encode("utf-8"), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b"tc3_request", hashlib.sha256).digest()
        return hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    # ---------- 调用 ----------
    def search(self, query: str, mode: int | None = None, cnt: int | None = None,
               freshness: str | None = None, industry: str | None = None,
               site: str | None = None, timeout: int = 20) -> dict:
        """Mode=0 自然检索结果；Mode=1 含 VR 权威信源卡。
        注意：Cnt 只接受 10/20/30/40/50，传其它值会静默返回 Error（不抛异常）。"""
        params: dict = {"Query": query}
        if mode is not None:
            params["Mode"] = mode
        if cnt is not None:
            params["Cnt"] = cnt
        if freshness is not None:
            params["Freshness"] = freshness
        if industry is not None:
            params["Industry"] = industry
        if site is not None:
            params["Site"] = site

        payload = json.dumps(params).encode("utf-8")
        timestamp = int(time.time())
        signature = self._sign(timestamp, payload)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Host": HOST,
            "X-TC-Action": ACTION,
            "X-TC-Version": VERSION,
            "X-TC-Timestamp": str(timestamp),
            "Authorization": (
                f"TC3-HMAC-SHA256 Credential={self.secret_id}/"
                f"{time.strftime('%Y-%m-%d', time.gmtime(timestamp))}/{SERVICE}/tc3_request, "
                f"SignedHeaders=content-type;host;x-tc-action, Signature={signature}"
            ),
        }

        req = urllib.request.Request(f"https://{HOST}", data=payload, headers=headers, method="POST")
        self.calls += 1
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"HTTPError": e.code, "body": e.read().decode("utf-8", "ignore")}

    def pages(self, query: str, **kw) -> list[dict]:
        """返回解析后的 Pages 列表（每条为 dict）。VR 卡含 vr/vr_category/vrid 字段。
        Response.Error 结构不抛 HTTP 异常，这里显式转成 RuntimeError，避免静默失败。"""
        raw = self.search(query, **kw)
        if "HTTPError" in raw:
            raise RuntimeError(f"HTTP {raw['HTTPError']}: {raw.get('body', '')[:200]}")
        resp = raw.get("Response")
        if not resp:
            raise RuntimeError(f"接口返回异常: {json.dumps(raw, ensure_ascii=False)[:300]}")
        if "Error" in resp:
            err = resp["Error"]
            raise RuntimeError(f"API 错误: {err.get('Code')} - {err.get('Message')} (query={query})")
        out = []
        for p in resp.get("Pages", []):
            if isinstance(p, str):
                try:
                    out.append(json.loads(p))
                except json.JSONDecodeError:
                    out.append({"_raw": p})
            else:
                out.append(p)
        return out

    def vr_cards(self, query: str, **kw) -> list[dict]:
        """只取 VR 权威信源卡（vr 为真且带 passage）"""
        return [p for p in self.pages(query, **kw) if p.get("vr")]


if __name__ == "__main__":
    import sys
    c = WsaClient()
    r = c.search(sys.argv[1] if len(sys.argv) > 1 else "腾讯股价", mode=1, cnt=10)
    print(json.dumps(r, ensure_ascii=False, indent=2)[:2000])
