import asyncio


async def delay(sleep: int, coroutine):
    asyncio.sleep(sleep)
    await coroutine
