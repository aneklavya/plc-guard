"""Drive the OpenPLC v3 web interface: log in, upload an ST program, compile it,
start the runtime. Standard library only.

OpenPLC's web UI has no API for this, so we post the same forms a browser
would. Default credentials are openplc / openplc (and they are compared in
plain text by the server, which is itself a lesson in ICS security).
"""
from __future__ import annotations

import http.cookiejar
import re
import time
import urllib.parse
import urllib.request
import uuid

CONFIG_TEMPLATE = """
CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms, PRIORITY := 0);
    PROGRAM instance0 WITH task0 : {program};
  END_RESOURCE
END_CONFIGURATION
"""


def with_configuration(source: str) -> str:
    """OpenPLC needs a CONFIGURATION: one task scanning the program every 20 ms."""
    if re.search(r"\bCONFIGURATION\b", source, re.I):
        return source
    name = re.search(r"\bPROGRAM\s+(\w+)", source, re.I).group(1)
    return source.rstrip() + "\n" + CONFIG_TEMPLATE.format(program=name)


class OpenPLC:
    def __init__(self, url: str = "http://127.0.0.1:8080", user: str = "openplc",
                 password: str = "openplc"):
        self.url = url.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self._post("/login", {"username": user, "password": password})

    def _get(self, path: str) -> str:
        with self.opener.open(self.url + path, timeout=60) as r:
            return r.read().decode(errors="replace")

    def _post(self, path: str, fields: dict) -> str:
        data = urllib.parse.urlencode(fields).encode()
        with self.opener.open(self.url + path, data, timeout=60) as r:
            return r.read().decode(errors="replace")

    def _post_file(self, path: str, field: str, filename: str, content: bytes) -> str:
        boundary = uuid.uuid4().hex
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; "
                f"filename=\"{filename}\"\r\nContent-Type: text/plain\r\n\r\n").encode() \
            + content + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(self.url + path, body, {
            "Content-Type": f"multipart/form-data; boundary={boundary}"})
        with self.opener.open(req, timeout=60) as r:
            return r.read().decode(errors="replace")

    def stop(self) -> None:
        self._get("/stop_plc")

    def deploy(self, source: str, name: str, timeout: float = 300) -> str:
        """Upload, compile and start `source`. Returns the compilation log."""
        self.stop()
        page = self._post_file("/upload-program", "file", f"{name}.st",
                               with_configuration(source).encode())
        m = re.search(r"name=['\"]prog_file['\"][^>]*value=['\"]([^'\"]+)['\"]", page) or \
            re.search(r"value=['\"](\d+\.st)['\"]", page)
        if not m:
            raise RuntimeError("upload failed: could not find the stored file name")
        self._post("/upload-program-action", {
            "prog_name": name, "prog_descr": "PLCGuard demo", "prog_file": m.group(1),
            "epoch_time": str(int(time.time()))})
        self._get(f"/compile-program?file={m.group(1)}")
        deadline = time.time() + timeout
        log = ""
        while time.time() < deadline:
            time.sleep(2)
            log = self._get("/compilation-logs")
            if "Compilation finished successfully" in log:
                self._get("/start_plc")
                time.sleep(3)
                return log
            if re.search(r"error|Error", log) and "finished" in log.lower():
                break
        raise RuntimeError("compilation failed or timed out:\n" + log[-2000:])
