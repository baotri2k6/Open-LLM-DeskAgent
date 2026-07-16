"""
Unit tests cho utils/stream_helpers.py — fanout multiplexor.
Chạy: python -m pytest tests/unit/test_stream_helpers.py -v
"""
import asyncio
import pytest
import sys
import os

# Đảm bảo import được utils từ project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.stream_helpers import fanout

pytestmark = pytest.mark.anyio


@pytest.mark.anyio
async def test_fanout_basic():
    """Fanout cơ bản: 2 consumers nhận đủ 5 items."""
    items_a = []
    items_b = []

    async def source():
        for i in range(5):
            yield {"n": i}

    async def consumer_a(stream):
        async for item in stream:
            items_a.append(item["n"])

    async def consumer_b(stream):
        async for item in stream:
            items_b.append(item["n"])

    await fanout(source(), [consumer_a, consumer_b])
    assert items_a == [0, 1, 2, 3, 4]
    assert items_b == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_fanout_empty_source():
    """Fanout với source rỗng — consumers kết thúc ngay."""
    items = []

    async def source():
        return
        yield  # make it a generator

    async def consumer(stream):
        async for item in stream:
            items.append(item)

    await fanout(source(), [consumer])
    assert items == []


@pytest.mark.asyncio
async def test_fanout_no_consumers():
    """Fanout không có consumer — source được drain, không crash."""
    async def source():
        for i in range(3):
            yield {"n": i}

    # Phải không crash
    await fanout(source(), [])


@pytest.mark.asyncio
async def test_fanout_single_consumer():
    """Fanout với 1 consumer."""
    items = []

    async def source():
        for i in range(3):
            yield i

    async def consumer(stream):
        async for item in stream:
            items.append(item)

    await fanout(source(), [consumer])
    assert items == [0, 1, 2]


@pytest.mark.asyncio
async def test_fanout_consumers_independent():
    """Mỗi consumer nhận toàn bộ items độc lập — slow consumer không block fast consumer."""
    fast_done = asyncio.Event()
    items_fast = []
    items_slow = []

    async def source():
        for i in range(3):
            yield i

    async def fast_consumer(stream):
        async for item in stream:
            items_fast.append(item)
        fast_done.set()

    async def slow_consumer(stream):
        async for item in stream:
            await asyncio.sleep(0.01)  # Simulate slow processing
            items_slow.append(item)

    await fanout(source(), [fast_consumer, slow_consumer])
    assert items_fast == [0, 1, 2]
    assert items_slow == [0, 1, 2]
    assert fast_done.is_set()
