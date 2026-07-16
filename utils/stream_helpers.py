"""
Fan-out một async generator đến nhiều consumer song song.

Port từ J.A.I.son multiplexor.py — đơn giản hóa cho DeskAgent use case.

Usage:
    from utils.stream_helpers import fanout

    async def tts_consumer(stream):
        async for item in stream:
            await audio_streamer.feed_text(item["text"])

    async def emotion_consumer(stream):
        async for item in stream:
            emotion = detect_emotion(item["text"])
            if emotion: send_chunk({"type": "emotion", "emotion": emotion})

    await fanout(llm_stream, [tts_consumer, emotion_consumer])
"""
import asyncio
from typing import AsyncGenerator, Callable, List


async def fanout(
    source: AsyncGenerator,
    consumers: List[Callable[[AsyncGenerator], None]]
):
    """
    Broadcast từng item từ source đến tất cả consumers chạy song song.

    Args:
        source: AsyncGenerator nguồn (ví dụ: LLM token stream)
        consumers: List các async functions nhận items từ source

    Mỗi consumer nhận một async generator độc lập trỏ đến cùng dữ liệu.
    Broadcast task đọc source một lần và push vào từng queue.
    Tất cả chạy concurrently — không có consumer nào block consumer khác.
    """
    if not consumers:
        # Không có consumer — drain source
        async for _ in source:
            pass
        return

    # Tạo queue riêng cho mỗi consumer
    queues: List[asyncio.Queue] = [asyncio.Queue() for _ in consumers]
    done_events: List[asyncio.Event] = [asyncio.Event() for _ in consumers]

    # Fan-out task: đọc source và broadcast đến tất cả queues
    async def broadcast():
        try:
            async for item in source:
                for q in queues:
                    await q.put(item)
        finally:
            # Signal tất cả consumers rằng source đã kết thúc
            for event in done_events:
                event.set()

    # Wrapper: chuyển queue → async generator cho từng consumer
    async def queue_to_gen(q: asyncio.Queue, done: asyncio.Event):
        while True:
            try:
                item = q.get_nowait()
                yield item
                q.task_done()
            except asyncio.QueueEmpty:
                if done.is_set() and q.empty():
                    break
                await asyncio.sleep(0)

    # Chạy broadcast và tất cả consumers song song
    broadcast_task = asyncio.create_task(broadcast())
    consumer_tasks = [
        asyncio.create_task(consumers[i](queue_to_gen(queues[i], done_events[i])))
        for i in range(len(consumers))
    ]

    await asyncio.gather(broadcast_task, *consumer_tasks)
