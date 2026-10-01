"""Parallel ranged download that survives stalls: pget.py URL PATH [PARTS].

HF's CDN stalls single long connections; N ranged connections are faster and each part
resumes from where it stopped (progress kept in PATH.parts across restarts).
"""

import os
import sys
import threading
import time
from pathlib import Path

import httpx


def main(url: str, path: str, parts: int = 8) -> None:
    size = int(httpx.head(url, follow_redirects=True).headers["content-length"])
    state = path + ".parts"
    if os.path.exists(path) and os.path.getsize(path) == size and not os.path.exists(state):
        return
    with open(path, "ab") as f:
        f.truncate(size)
    saved = Path(state).read_text().split() if os.path.exists(state) else ["0"] * parts
    done = [int(x) for x in saved]
    step = -(-size // parts)

    def worker(i: int) -> None:
        start, end = i * step, min(size, (i + 1) * step) - 1
        while start + done[i] <= end:
            try:
                kw = {"headers": {"Range": f"bytes={start + done[i]}-{end}"}, "timeout": 30}
                with (
                    httpx.stream("GET", url, follow_redirects=True, **kw) as r,
                    open(path, "r+b") as f,
                ):
                    f.seek(start + done[i])
                    for chunk in r.iter_bytes(1 << 20):
                        f.write(chunk)
                        done[i] += len(chunk)
            except httpx.HTTPError:
                time.sleep(2)

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(parts)]
    for t in threads:
        t.start()
    last = sum(done)
    while any(t.is_alive() for t in threads):
        time.sleep(30)
        with open(state, "w") as f:
            f.write(" ".join(map(str, done)))
        now = sum(done)
        print(f"{now / 1e9:.2f}/{size / 1e9:.2f} GB  {(now - last) / 30e6:.1f} MB/s", flush=True)
        last = now
    os.remove(state)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *map(int, sys.argv[3:]))
