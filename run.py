# -*- cofing: utf-8 -*-
# MIT License
#
# Copyright (c) 2021 - Present nxtlo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import os
import asyncio
import subprocess as sp
import logging
import threading

from core.client import main
_log = logging.getLogger("run")

if os.name != "nt":
    try:
        import uvloop
    except ImportError:
        i = input("uvloop is not installed, Do you want to install it?: ")
        if i in {"yes", "YES", "y", "Y"}:
            os.system(f"python -m pip install uvloop {'-U' if os.name != 'nt' else '--user'}")
        else:
            pass
    else:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

def _run_redis() -> sp.Popen[bytes]:
    with sp.Popen(["redis-server"], shell=False, stderr=sp.PIPE, stdout=sp.PIPE) as proc:
        ok, err = proc.communicate()
        if ok:
            _log.info("Redis server started.")
        elif err:
            raise RuntimeError("Couldn't start redis server", err)
    return proc


if __name__ == "__main__":
    t = threading.Thread(target=_run_redis)
    t.start()
    main()
    t.join()
