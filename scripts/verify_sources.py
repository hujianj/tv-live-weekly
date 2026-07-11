#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import concurrent.futures as cf
import csv
import gzip
import html
import ipaddress
import json
import re
import socket
import ssl
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 8
FETCH_TIMEOUT = 20
MAX_WORKERS = 64
CHECK_WORKERS = 96
MAX_URLS_PER_NAME = 8
MAX_VALID_PER_NAME = 5
UA = "Player"

SOURCES = [
    ("?????", "https://www.iyouhun.com/tv/zb"),
    ("????IPV4", "https://live.zbds.top/tv/iptv4.txt"),
    ("??IPTV", "https://develop202.github.io/migu_video/interface.txt"),
    ("??AI??TXT", "https://raw.githubusercontent.com/PizazzGY/TV/master/output/user_result.txt"),
    ("??AI??M3U", "https://raw.githubusercontent.com/PizazzGY/TV/master/output/user_result.m3u"),
    ("Guovin??", "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u"),
    ("Guovin IPv4", "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/ipv4/result.m3u"),
    ("Guovin IPv6", "https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/ipv6/result.m3u"),
    ("myIPTV IPv4", "https://raw.githubusercontent.com/suxuang/myIPTV/refs/heads/main/ipv4.m3u"),
    ("myIPTV IPv6", "https://raw.githubusercontent.com/suxuang/myIPTV/refs/heads/main/ipv6.m3u"),
    ("????IPV4 M3U", "https://live.zbds.top/tv/iptv4.m3u"),
    ("BurningC4", "https://raw.githubusercontent.com/BurningC4/Chinese-IPTV/master/TV-IPV4.m3u"),
    ("???", "https://raw.githubusercontent.com/vamoschuck/TV/main/M3U"),
    ("????IPV6 TXT", "https://live.zbds.top/tv/iptv6.txt"),
    ("????IPV6 M3U", "https://live.zbds.top/tv/iptv6.m3u"),
    ("fanmingming IPv6", "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u"),
    ("fanmingming??", "https://live.fanmingming.cn/tv/m3u/ipv6.m3u"),
    ("YueChan", "https://raw.githubusercontent.com/YueChan/Live/main/IPTV.m3u"),
    ("gitee dsy", "https://gitee.com/xxy002/zhiboyuan/raw/master/dsy"),
    ("Kimentanm", "https://raw.githubusercontent.com/Kimentanm/aptv/master/m3u/iptv.m3u"),
    ("BigBigGrandG", "https://raw.githubusercontent.com/BigBigGrandG/IPTV-URL/release/Gather.m3u"),
    ("YanG??", "https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u"),
    ("JackTV??", "https://php.946985.filegear-sg.me/jackTV.m3u"),
    ("iptv-org??", "https://iptv-org.github.io/iptv/index.m3u"),
    ("utako??", "https://web.utako.moe/jp.m3u"),
    ("epg??", "https://epg.pw/test_channels.m3u"),
    ("epg??", "https://epg.pw/test_channels_hong_kong.m3u"),
    ("epg??", "https://epg.pw/test_channels_macau.m3u"),
    ("epg??", "https://epg.pw/test_channels_taiwan.m3u"),
    ("iptv-org??", "https://iptv-org.github.io/iptv/countries/tw.m3u"),
    ("epg???", "https://epg.pw/test_channels_singapore.m3u"),
    ("epg????", "https://epg.pw/test_channels_malaysia.m3u"),
    ("Free-TV??", "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"),
    ("?????", "https://live.freetv.top/huyayqk.m3u"),
    ("?????", "https://live.freetv.top/douyuyqk.m3u"),
    ("YY??", "https://gongdian.top/tv/Mursor/yylunbo.m3u"),
    ("??????", "https://gongdian.top/tv/Mursor/bililive.m3u"),
]

BAD_MARKERS = ("nosignal", "no-signal", "no_signal", "notfound", "404", "offline")
BAD_HTML = (b"<html", b"<!doctype html", b"<head", b"<body")
MEDIA_EXTS = (".ts", ".m4s", ".mp4", ".aac", ".mp3", ".flv")

@dataclass(frozen=True)
class Candidate:
    source: str
    group: str
    name: str
    url: str

@dataclass
class SourceStatus:
    name: str
    url: str
    ok: bool
    bytes: int = 0
    parsed: int = 0
    error: str = ""

@dataclass
class CheckResult:
    cand: Candidate
    ok: bool
    detail: str


def decode_bytes(data: bytes, content_type: str = "") -> str:
    # Most Chinese IPTV lists are UTF-8; fall back to gb18030 only when needed.
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def fetch_url(url: str, timeout: int = FETCH_TIMEOUT, max_bytes: int = 12_000_000) -> tuple[int, str, bytes, str]:
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Connection": "close"})
    with urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        code = getattr(r, "status", 200)
        ctype = r.headers.get("Content-Type") or ""
        data = r.read(max_bytes)
        final = r.geturl()
    if url.endswith(".gz") or "gzip" in (ctype.lower()):
        try:
            data = gzip.decompress(data)
        except Exception:
            pass
    return code, ctype, data, final


def normalize_name(name: str) -> str:
    name = html.unescape(name or "").strip().strip('"').strip("'")
    name = re.sub(r"\s+", "", name)
    if name.startswith("\u4e2d\u592e"):
        name = name.replace("\u4e2d\u592e", "CCTV", 1)
    return name[:80] or "\u672a\u547d\u540d\u9891\u9053"


def infer_group(name: str, group: str = "") -> str:
    G_CCTV = "\u592e\u89c6\u9891\u9053"
    G_SAT = "\u536b\u89c6\u9891\u9053"
    G_HK = "\u6d77\u5916\u53ca\u6e2f\u53f0"
    G_LOOP = "\u8f6e\u64ad\u9891\u9053"
    G_OTHER = "\u5176\u4ed6\u9891\u9053"
    g = (group or "").strip()
    n = name.upper()
    if "CCTV" in n or name.startswith("\u592e\u89c6") or name.startswith("\u4e2d\u592e") or "CGTN" in n:
        return G_CCTV
    if "\u536b\u89c6" in name:
        return G_SAT
    if any(x in g for x in ("\u9999\u6e2f", "\u6fb3\u95e8", "\u53f0\u6e7e", "\u6d77\u5916", "\u65e5\u672c", "\u65b0\u52a0\u5761", "\u9a6c\u6765\u897f\u4e9a")):
        return G_HK
    if any(x in g.lower() for x in ("movie", "sport", "news", "kids")):
        return G_HK
    if any(x in g for x in ("\u864e\u7259", "\u6597\u9c7c", "\u8f6e\u64ad", "\u54d4\u54e9")):
        return G_LOOP
    return g or G_OTHER

def parse_m3u(text: str, source: str) -> list[Candidate]:
    out: list[Candidate] = []
    last_name = ""
    last_group = ""
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        if line.startswith("#EXTINF"):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
            tail = line.split(",", 1)[1].strip() if "," in line else ""
            last_name = normalize_name(attrs.get("tvg-name") or tail or attrs.get("title") or "")
            last_group = attrs.get("group-title") or ""
        elif line.startswith("#"):
            continue
        elif re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", line):
            if line.startswith(("http://", "https://", "rtmp://")):
                name = normalize_name(last_name or urlparse(line).path.rsplit("/", 1)[-1])
                group = infer_group(name, last_group)
                out.append(Candidate(source, group, name, line))
            last_name = ""
            last_group = ""
    return out


def parse_txt(text: str, source: str) -> list[Candidate]:
    out: list[Candidate] = []
    group = ""
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        if line.endswith(",#genre#"):
            group = line.split(",", 1)[0].strip()
            continue
        if "," in line:
            name, url = line.split(",", 1)
        elif " " in line:
            name, url = line.split(None, 1)
        else:
            continue
        name = normalize_name(name)
        url = url.strip()
        if url.startswith(("http://", "https://", "rtmp://")):
            out.append(Candidate(source, infer_group(name, group), name, url))
    return out


def parse_playlist(text: str, source: str) -> list[Candidate]:
    if "#EXTM3U" in text[:2000] or "#EXTINF" in text[:5000]:
        return parse_m3u(text, source)
    return parse_txt(text, source)


def fetch_source(item: tuple[str, str]) -> tuple[SourceStatus, list[Candidate]]:
    name, url = item
    try:
        code, ctype, data, final = fetch_url(url)
        text = decode_bytes(data, ctype)
        cands = parse_playlist(text, name)
        st = SourceStatus(name, url, True, len(data), len(cands), "")
        return st, cands
    except Exception as e:
        return SourceStatus(name, url, False, 0, 0, repr(e)[:240]), []


def is_ipv6_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    try:
        return isinstance(ipaddress.ip_address(host), ipaddress.IPv6Address)
    except Exception:
        return ":" in host and not re.match(r"^\d+\.\d+\.\d+\.\d+$", host)


def http_get_small(url: str, max_bytes: int = 65536, timeout: int = TIMEOUT) -> tuple[int, str, bytes, str]:
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Connection": "close"})
    with urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        code = getattr(r, "status", 200)
        ctype = (r.headers.get("Content-Type") or "").lower()
        data = r.read(max_bytes)
        final = r.geturl()
    return code, ctype, data, final


def looks_bad(data: bytes, text: str = "") -> bool:
    sample = (text or data[:4096].decode("utf-8", "ignore")).lower()
    if any(m in sample for m in BAD_MARKERS):
        return True
    if any(x in data[:256].lower() for x in BAD_HTML):
        return True
    return False


def parse_next_from_m3u8(text: str, base: str) -> tuple[str | None, str | None]:
    if any(m in text.lower() for m in BAD_MARKERS):
        return None, None
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            for nxt in lines[i+1:]:
                if not nxt.startswith("#"):
                    return "playlist", urljoin(base, nxt)
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            for nxt in lines[i+1:]:
                if not nxt.startswith("#"):
                    return "segment", urljoin(base, nxt)
    for line in lines:
        if not line.startswith("#") and any(ext in line.lower() for ext in MEDIA_EXTS + (".m3u8",)):
            return ("playlist" if ".m3u8" in line.lower() else "segment"), urljoin(base, line)
    return None, None


def looks_media(data: bytes, ctype: str) -> bool:
    if looks_bad(data):
        return False
    if len(data) < 188:
        return False
    if data[:1] == b"G" or data[:1] == b"\x47":
        return True
    if data[:4] in (b"\x00\x00\x00\x18", b"\x00\x00\x00 ") or b"ftyp" in data[:32]:
        return True
    if any(x in ctype for x in ("video", "audio", "octet-stream", "mp2t")):
        return True
    return False


def check_candidate(cand: Candidate) -> CheckResult:
    url = cand.url.strip()
    if not url.startswith(("http://", "https://")):
        return CheckResult(cand, False, "unsupported scheme")
    # For home Ku9 on common networks, IPv6-only URLs often fail; still test, but mark fail on network error.
    try:
        code, ctype, data, final = http_get_small(url)
        if code >= 400:
            return CheckResult(cand, False, f"http {code}")
        if looks_bad(data):
            return CheckResult(cand, False, "bad marker/html")
        text = data.decode("utf-8", "ignore")
        if "#EXTM3U" in text or "mpegurl" in ctype or url.lower().endswith((".m3u8", ".m3u")):
            kind, nxt = parse_next_from_m3u8(text, final)
            if not nxt:
                return CheckResult(cand, False, "playlist no media")
            if kind == "playlist":
                c2, ct2, d2, f2 = http_get_small(nxt)
                if c2 >= 400 or looks_bad(d2):
                    return CheckResult(cand, False, f"child bad {c2}")
                t2 = d2.decode("utf-8", "ignore")
                kind2, seg = parse_next_from_m3u8(t2, f2)
                if not seg:
                    return CheckResult(cand, False, "child no segment")
                c3, ct3, d3, f3 = http_get_small(seg, max_bytes=2048)
                return CheckResult(cand, looks_media(d3, ct3), f"variant->{c3} {ct3} bytes={len(d3)}")
            else:
                c2, ct2, d2, f2 = http_get_small(nxt, max_bytes=2048)
                return CheckResult(cand, looks_media(d2, ct2), f"segment->{c2} {ct2} bytes={len(d2)}")
        else:
            return CheckResult(cand, looks_media(data, ctype), f"direct {ctype} bytes={len(data)}")
    except Exception as e:
        return CheckResult(cand, False, repr(e)[:160])


def prefer_score(c: Candidate) -> tuple[int, int, str]:
    u = c.url.lower()
    # Ku9 ???????? http ipv4 ???? https?IPv6/?? CDN ???
    score = 0
    if u.startswith("http://"):
        score -= 20
    if "live.zbds.top" in c.source or "ipv4" in c.source.lower():
        score -= 10
    if "epg.pw" in u:
        score += 15
    if is_ipv6_url(c.url):
        score += 30
    return (score, len(c.url), c.source)


def main() -> None:
    start = time.time()
    print(f"Fetching {len(SOURCES)} sources...", flush=True)
    statuses: list[SourceStatus] = []
    all_cands: list[Candidate] = []
    with cf.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(SOURCES))) as ex:
        futs = [ex.submit(fetch_source, item) for item in SOURCES]
        for fut in cf.as_completed(futs):
            st, cands = fut.result()
            statuses.append(st)
            all_cands.extend(cands)
            print(f"source {'OK' if st.ok else 'FAIL'} {st.name}: parsed={st.parsed} bytes={st.bytes} {st.error}", flush=True)

    # Deduplicate and cap per channel before expensive checking.
    dedup: dict[tuple[str, str], Candidate] = {}
    for c in all_cands:
        name = normalize_name(c.name)
        if not name or len(c.url) > 1000:
            continue
        dedup.setdefault((name, c.url), Candidate(c.source, infer_group(name, c.group), name, c.url))
    by_name: dict[str, list[Candidate]] = {}
    for c in dedup.values():
        by_name.setdefault(c.name, []).append(c)
    to_check: list[Candidate] = []
    for name, arr in by_name.items():
        arr = sorted(arr, key=prefer_score)
        to_check.extend(arr[:MAX_URLS_PER_NAME])
    print(f"Parsed candidates={len(all_cands)}, unique={len(dedup)}, checking={len(to_check)}", flush=True)

    results: list[CheckResult] = []
    with cf.ThreadPoolExecutor(max_workers=CHECK_WORKERS) as ex:
        futs = [ex.submit(check_candidate, c) for c in to_check]
        for i, fut in enumerate(cf.as_completed(futs), 1):
            r = fut.result()
            results.append(r)
            if i % 100 == 0 or i == len(futs):
                ok = sum(1 for x in results if x.ok)
                print(f"checked {i}/{len(futs)}, ok={ok}", flush=True)

    valid_by_name: dict[str, list[Candidate]] = {}
    for r in results:
        if r.ok:
            valid_by_name.setdefault(r.cand.name, []).append(r.cand)
    valid: list[Candidate] = []
    for name, arr in valid_by_name.items():
        arr = sorted(arr, key=prefer_score)
        valid.extend(arr[:MAX_VALID_PER_NAME])

    group_order = ["\u592e\u89c6\u9891\u9053", "\u536b\u89c6\u9891\u9053", "\u5730\u65b9\u9891\u9053", "\u6d77\u5916\u53ca\u6e2f\u53f0", "\u8f6e\u64ad\u9891\u9053", "\u5176\u4ed6\u9891\u9053"]
    valid.sort(key=lambda c: (group_order.index(c.group) if c.group in group_order else 99, c.name, prefer_score(c)))

    txt_lines: list[str] = []
    for group in group_order + sorted(set(c.group for c in valid) - set(group_order)):
        rows = [c for c in valid if c.group == group]
        if not rows:
            continue
        if txt_lines:
            txt_lines.append("")
        txt_lines.append(f"{group},#genre#")
        for c in rows:
            txt_lines.append(f"{c.name},{c.url}")
    live_txt = "\n".join(txt_lines).strip() + "\n"
    (ROOT / "live.txt").write_bytes(live_txt.encode("utf-8"))
    (ROOT / "ku9-live.txt").write_bytes(live_txt.encode("utf-8"))

    m3u = ["#EXTM3U"]
    for c in valid:
        m3u.append(f'#EXTINF:-1 tvg-name="{c.name}" group-title="{c.group}",{c.name}')
        m3u.append(c.url)
    (ROOT / "live.m3u").write_text("\n".join(m3u) + "\n", encoding="utf-8", newline="\n")

    with (ROOT / "sources_status.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "url", "fetch_ok", "bytes", "parsed", "error"])
        for st in statuses:
            w.writerow([st.name, st.url, st.ok, st.bytes, st.parsed, st.error])

    with (ROOT / "stream_check_results.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ok", "group", "name", "url", "source", "detail"])
        for r in sorted(results, key=lambda x: (not x.ok, x.cand.group, x.cand.name)):
            w.writerow([r.ok, r.cand.group, r.cand.name, r.cand.url, r.cand.source, r.detail])

    ok_sources: dict[str, int] = {}
    for c in valid:
        ok_sources[c.source] = ok_sources.get(c.source, 0) + 1
    report = [
        "# IPTV source verification report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Elapsed: {time.time()-start:.1f}s",
        f"Sources total: {len(SOURCES)}",
        f"Sources fetched OK: {sum(1 for s in statuses if s.ok)}",
        f"Parsed candidates: {len(all_cands)}",
        f"Unique candidates: {len(dedup)}",
        f"Checked candidates: {len(to_check)}",
        f"Playable channel names: {len(valid_by_name)}",
        f"Published playable lines: {len(valid)}",
        "",
        "## Source fetch status",
        "",
        "| Source | Fetch | Parsed | Bytes | Error |",
        "|---|---:|---:|---:|---|",
    ]
    for st in statuses:
        report.append(f"| {st.name} | {'OK' if st.ok else 'FAIL'} | {st.parsed} | {st.bytes} | {st.error.replace('|','/')} |")
    report += ["", "## Published playable lines by source", "", "| Source | Lines |", "|---|---:|"]
    for src, n in sorted(ok_sources.items(), key=lambda x: (-x[1], x[0])):
        report.append(f"| {src} | {n} |")
    report += ["", "## First 80 published channels", ""]
    for c in valid[:80]:
        report.append(f"- {c.group} / {c.name} / {c.source}")
    (ROOT / "source-report.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    (ROOT / "check-report.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")

    print(f"DONE valid_names={len(valid_by_name)} valid_lines={len(valid)}", flush=True)
    print(f"Wrote live.txt bytes={(ROOT/'live.txt').stat().st_size}", flush=True)

if __name__ == "__main__":
    main()
