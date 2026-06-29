from __future__ import annotations

import asyncio
import inspect
import threading
from concurrent.futures import Future
from typing import Any


class SyncRunner:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="selenodriver-loop", daemon=True)
        self._thread.start()
        self._closed = False

    def run(self, value: Any) -> Any:
        if self._closed:
            raise RuntimeError("SyncRunner is closed")
        if not inspect.isawaitable(value):
            return value
        future = asyncio.run_coroutine_threadsafe(value, self._loop)
        return future.result()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        stop_future: Future[None] = asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
        stop_future.result(timeout=5)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
        self._loop.close()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _shutdown(self) -> None:
        tasks = [task for task in asyncio.all_tasks(self._loop) if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
