import asyncio
from collections.abc import AsyncIterator


class Broadcast[T]:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[T]] = set()

    async def publish(self, item: T) -> None:
        for queue in tuple(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(item)

    async def subscribe(self) -> AsyncIterator[T]:
        queue: asyncio.Queue[T] = asyncio.Queue(maxsize=4)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)
