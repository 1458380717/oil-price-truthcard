# -*- coding: utf-8 -*-
"""油价真伪卡 · 本地 Web 服务

零第三方依赖，标准库 http.server。
    python src/server.py            # http://127.0.0.1:8765
    python src/server.py --port 9000

两个接口：
    GET  /                         查询页
    POST /api/verify               {"city": "北京", "claim": "7.85"}  → 四态判定
    GET  /api/health               自检
"""
import argparse
import json
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wsa_client import WsaClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE_TTL = 60          # 同城 60 秒内复用，省额度
GRADE_RE = re.compile(r"国内燃油标号：(\d+)号")
TODAY_RE = re.compile(r"今日油价（元每升）：([\d.]+)")
HIST_RE = re.compile(r"历史油价（元每升）：([\d.]+)")
CLAIM_RE = re.compile(r"\d{1,2}\.\d{1,2}\s*元?\s*/?\s*升?")

_client = None
_cache: dict[str, tuple[float, dict]] = {}


def client():
    global _client
    if _client is None:
        _client = WsaClient(env_file=str(ROOT / ".env"))
    return _client


def parse_card(passage: str) -> dict:
    """把 VR 卡 passage 解析成 {grades: {92: {today, history}}}"""
    grades = {}
    blocks = passage.split("国内燃油标号：")[1:]
    for b in blocks:
        g = GRADE_RE.match("国内燃油标号：" + b)
        if not g:
            continue
        grade = g.group(1)
        today = TODAY_RE.search(b[:200])
        hist = HIST_RE.search(b[:200])
        grades[grade] = {
            "today": float(today.group(1)) if today else None,
            "history": float(hist.group(1)) if hist else None,
        }
    city = re.search(r"#\s*城市：(.+)", passage)
    date = re.search(r"#\s*日期：(.+)", passage)
    return {
        "city": city.group(1).strip() if city else "",
        "date": date.group(1).strip() if date else "",
        "grades": grades,
    }


def judge(asserted, today, history):
    """四态判定。整数分比较，避开浮点边界抖动。"""
    a = int(round(asserted * 100))
    if today is not None and a == int(round(today * 100)):
        return "correct"
    if history is not None and a == int(round(history * 100)):
        return "stale"
    return "mismatch"


def fetch_city(city: str, grade: str = "92") -> dict:
    key = f"{city}|{grade}"
    now = time.time()
    if key in _cache and now - _cache[key][0] < CACHE_TTL:
        d = dict(_cache[key][1])
        d["cached"] = True
        return d

    c = client()
    pages = c.pages(f"{city} {grade} 号汽油 价格", mode=1, cnt=10)
    cards = [p for p in pages if p.get("vr") and p.get("vr_category") == "oil"]
    if not cards:
        d = {"city": city, "grade": grade, "found": False,
             "state": "unknown", "message": "无权威数据，判存疑",
             "calls": c.calls}
        _cache[key] = (now, d)
        return d

    parsed = parse_card(cards[0].get("passage") or "")
    g = parsed["grades"].get(grade) or {}
    d = {
        "city": city, "grade": grade, "found": True,
        "card_city": parsed["city"], "date": parsed["date"],
        "today": g.get("today"), "history": g.get("history"),
        "delta": (round(g["today"] - g["history"], 2)
                  if g.get("today") is not None and g.get("history") is not None else None),
        "site": cards[0].get("site"), "calls": c.calls, "cached": False,
    }
    _cache[key] = (now, d)
    return d


class Handler(BaseHTTPRequestHandler):
    server_version = "OilTruthcard/1.0"

    def log_message(self, fmt, *a):
        sys.stderr.write("[srv] %s\n" % (fmt % a))

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            html = (ROOT / "docs" / "app.html")
            if html.exists():
                return self._send(200, html.read_bytes(), "text/html; charset=utf-8")
            return self._send(500, "docs/app.html 不存在")
        if u.path == "/api/health":
            return self._send(200, json.dumps({"ok": True, "calls": client().calls},
                                              ensure_ascii=False))
        if u.path == "/report":
            txt = (ROOT / "docs" / "油价真伪卡.html").read_text(encoding="utf-8")
            return self._send(200, txt, "text/html; charset=utf-8")
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/api/verify":
            return self._send(404, json.dumps({"error": "not found"}))
        n = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, json.dumps({"error": "bad json"}))

        city = (payload.get("city") or "").strip()
        claim_raw = str(payload.get("claim") or "").strip()
        grade = str(payload.get("grade") or "92")
        if not city:
            return self._send(400, json.dumps({"error": "缺少城市"}, ensure_ascii=False))

        m = re.search(r"\d{1,2}\.\d{1,2}", claim_raw)
        claim = float(m.group(0)) if m else None

        try:
            off = fetch_city(city, grade)
        except Exception as e:
            return self._send(502, json.dumps({"error": f"接口调用失败：{e}"}, ensure_ascii=False))

        out = {"official": off, "claim": claim}
        if not off.get("found"):
            out["verdict"] = "unknown"
            out["reason"] = "该城市没有成品油 VR 卡，无法判定"
        elif claim is None:
            out["verdict"] = "no_claim"
            out["reason"] = "没有从输入里抽到价格数字，不计入分母"
        else:
            out["verdict"] = judge(claim, off.get("today"), off.get("history"))
            gap_t = round(claim - (off.get("today") or 0), 2)
            gap_h = (round(claim - (off.get("history") or 0), 2)
                     if off.get("history") is not None else None)
            out["gap_vs_today"] = gap_t
            out["gap_vs_history"] = gap_h
            out["reason"] = {
                "correct": "与今日官方价一致",
                "stale": "等于上一轮价，曾经是真的，已过期",
                "mismatch": "今日、上一轮都不是",
            }[out["verdict"]]
        return self._send(200, json.dumps(out, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"油价真伪卡 · http://{a.host}:{a.port}")
    print(f"项目根目录 {ROOT}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
