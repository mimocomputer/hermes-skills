#!/usr/bin/env python3
"""Minimal CDP driver for a cloud browser session (Browser-Use or any CDP endpoint).

    cdp.py [--session PATH] create [--profile UUID] [--proxy de] [--timeout 240]
    cdp.py [--session PATH] ip                 # public IP of the browser (proxy check)
    cdp.py [--session PATH] nav URL            # navigate, print url + title
    cdp.py [--session PATH] text [LIMIT]       # visible page text
    cdp.py [--session PATH] html [LIMIT]       # raw outerHTML
    cdp.py [--session PATH] cookies [DOMAIN]   # cookies (domain, name, expiry)
    cdp.py [--session PATH] click SELECTOR
    cdp.py [--session PATH] fill SELECTOR TEXT
    cdp.py [--session PATH] js EXPRESSION

create writes/updates the session JSON (id, cdpUrl, liveUrl) with mode 0600 and
prints only the liveUrl, so a control URL never lands in a transcript by accident.
Needs: pip install --user websockets
"""
import asyncio, json, os, re, stat, sys, urllib.request
from pathlib import Path

API = "https://api.browser-use.com/api/v3/browsers"
KEY_ENV = "BROWSER_USE_API_KEY"


def _key():
    k = os.environ.get(KEY_ENV)
    if k:
        return k.strip()
    for env in (Path.home() / ".hermes" / ".env", Path.home() / ".env"):
        if env.exists():
            m = re.search(rf"^{KEY_ENV}=(.*)$", env.read_text(), re.M)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    sys.exit(f"{KEY_ENV} not found in environment or ~/.hermes/.env")


def create(session_path, profile=None, proxy=None, timeout=None):
    body = {}
    if profile:
        body["profileId"] = profile
    if proxy:
        body["proxyCountryCode"] = proxy.lower()
    if timeout:
        body["timeout"] = int(timeout)
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(), method="POST",
        headers={"X-Browser-Use-API-Key": _key(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)
    p = Path(session_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
    print("session id:", data.get("id"))
    print("timeout min:", body.get("timeout", "(default)"))
    print("liveUrl:", data.get("liveUrl"))


class Client:
    def __init__(self, ws):
        self.ws, self.i = ws, 0

    async def call(self, method, params=None, session=None):
        self.i += 1
        msg = {"id": self.i, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        await self.ws.send(json.dumps(msg))
        while True:
            data = json.loads(await self.ws.recv())
            if data.get("id") == self.i:
                if "error" in data:
                    raise RuntimeError(data["error"])
                return data.get("result", {})

    async def page(self):
        t = await self.call("Target.getTargets")
        for tgt in t["targetInfos"]:
            if tgt["type"] == "page" and "devtools" not in tgt.get("url", ""):
                r = await self.call("Target.attachToTarget",
                                    {"targetId": tgt["targetId"], "flatten": True})
                return r["sessionId"]
        r = await self.call("Target.createTarget", {"url": "about:blank"})
        a = await self.call("Target.attachToTarget",
                            {"targetId": r["targetId"], "flatten": True})
        return a["sessionId"]


async def run(cmd, arg, arg2, session_path):
    import websockets
    cfg = json.loads(Path(session_path).read_text())
    url = cfg["cdpUrl"].replace("https://", "wss://").replace("http://", "ws://")
    async with websockets.connect(url, max_size=32 * 1024 * 1024) as ws:
        c = Client(ws)
        sid = await c.page()
        await c.call("Page.enable", session=sid)
        await c.call("Runtime.enable", session=sid)

        async def js(expr):
            r = await c.call("Runtime.evaluate",
                             {"expression": expr, "returnByValue": True,
                              "awaitPromise": True}, session=sid)
            return r.get("result", {}).get("value")

        if cmd == "nav":
            await c.call("Page.navigate", {"url": arg}, session=sid)
            await asyncio.sleep(6)
            print("url:", await js("location.href"))
            print("title:", await js("document.title"))
        elif cmd in ("text", "html"):
            limit = int(arg or 4000)
            expr = ("document.body ? document.body.innerText : ''" if cmd == "text"
                    else "document.documentElement.outerHTML")
            print((await js(expr) or "")[:limit])
        elif cmd == "ip":
            await c.call("Page.navigate", {"url": "https://api.ipify.org?format=json"}, session=sid)
            await asyncio.sleep(4)
            print(await js("document.body.innerText"))
        elif cmd == "js":
            print(await js(arg))
        elif cmd == "click":
            await js(f'document.querySelector({json.dumps(arg)}).click()')
            await asyncio.sleep(2)
            print("clicked", arg)
        elif cmd == "fill":
            await js(f'(()=>{{const e=document.querySelector({json.dumps(arg)});'
                     f'e.focus();e.value={json.dumps(arg2 or "")};'
                     f'e.dispatchEvent(new Event("input",{{bubbles:true}}));return true;}})()')
            print("filled", arg)
        elif cmd == "cookies":
            # Network.enable is required before cookie/session domains answer.
            await c.call("Network.enable", session=sid)
            r = await c.call("Network.getAllCookies", session=sid)
            for ck in r.get("cookies", []):
                if arg and arg not in ck["domain"]:
                    continue
                print(f"{ck['domain']:34} {ck['name']:28} expires {ck.get('expires')}")
        else:
            print("unknown command", cmd)


if __name__ == "__main__":
    args = sys.argv[1:]
    path = "./session.json"
    if "--session" in args:
        i = args.index("--session")
        path = args[i + 1]
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    cmd = args[0]
    if cmd == "create":
        kw = {}
        for flag, name in (("--profile", "profile"), ("--proxy", "proxy"), ("--timeout", "timeout")):
            if flag in args:
                kw[name] = args[args.index(flag) + 1]
        create(path, **kw)
    else:
        asyncio.run(run(cmd, args[1] if len(args) > 1 else None,
                        args[2] if len(args) > 2 else None, path))
