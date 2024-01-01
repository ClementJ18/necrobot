import asyncio


async def delay(sleep: int, coroutine):
    return asyncio.create_task(_delay(sleep, coroutine))


async def _delay(sleep: int, coroutine):
    await asyncio.sleep(sleep)
    await coroutine
