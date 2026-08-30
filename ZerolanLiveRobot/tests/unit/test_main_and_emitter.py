"""Unit tests for main.py argument parsing and event emitter integration."""
import asyncio
import sys
from unittest.mock import patch, MagicMock

import pytest

from event.event_emitter import TypedEventEmitter, Listener
from event.event_data import BaseEvent


# --- main.py parse_args ---

@pytest.mark.unit
class TestParseArgs:
    def test_no_args(self):
        with patch("sys.argv", ["main.py"]):
            from main import parse_args
            args = parse_args()
            assert args.config is None

    def test_config_short(self):
        with patch("sys.argv", ["main.py", "-c", "/tmp/test.yaml"]):
            from main import parse_args
            args = parse_args()
            assert args.config == "/tmp/test.yaml"

    def test_config_long(self):
        with patch("sys.argv", ["main.py", "--config", "/tmp/test.yaml"]):
            from main import parse_args
            args = parse_args()
            assert args.config == "/tmp/test.yaml"


# --- TypedEventEmitter expanded tests ---

class PingEvent(BaseEvent):
    type: str = "test.ping"
    message: str = ""


class PongEvent(BaseEvent):
    type: str = "test.pong"
    reply: str = ""


@pytest.mark.unit
class TestTypedEventEmitter:
    def test_on_registers_listener(self):
        emitter = TypedEventEmitter()

        @emitter.on("test.ping")
        def handler(event):
            pass

        assert "test.ping" in emitter._listeners
        assert len(emitter._listeners["test.ping"]) == 1

    def test_once_registers_once_listener(self):
        emitter = TypedEventEmitter()

        @emitter.once("test.ping")
        def handler(event):
            pass

        assert len(emitter._listeners["test.ping"]) == 1
        assert emitter._listeners["test.ping"][0].once is True

    def test_emit_sync_handler(self):
        emitter = TypedEventEmitter()
        results = []

        @emitter.on("test.ping")
        def handler(event):
            results.append(event.message)

        emitter.emit(PingEvent(message="hello"))
        # Task is queued in sync executor; run it manually
        task = emitter._sync_executor._sync_tasks.get_nowait()
        task.execute()

        assert results == ["hello"]

    @pytest.mark.asyncio
    async def test_emit_async_handler(self):
        emitter = TypedEventEmitter()
        results = []

        @emitter.on("test.ping")
        async def handler(event):
            results.append(event.message)

        emitter.emit(PingEvent(message="async-hello"))
        task = emitter._async_executor._async_tasks.get_nowait()
        await task.execute()

        assert results == ["async-hello"]

    def test_emit_no_listeners(self):
        emitter = TypedEventEmitter()
        # Should not raise
        emitter.emit(PingEvent(message="no one listens"))

    def test_multiple_listeners(self):
        emitter = TypedEventEmitter()
        results = []

        @emitter.on("test.ping")
        def handler1(event):
            results.append("h1")

        @emitter.on("test.ping")
        def handler2(event):
            results.append("h2")

        emitter.emit(PingEvent())
        while not emitter._sync_executor._sync_tasks.empty():
            task = emitter._sync_executor._sync_tasks.get_nowait()
            task.execute()

        assert "h1" in results
        assert "h2" in results

    def test_once_listener_auto_removes(self):
        emitter = TypedEventEmitter()
        count = []

        @emitter.once("test.ping")
        def handler(event):
            count.append(1)

        # Emit twice
        emitter.emit(PingEvent())
        task = emitter._sync_executor._sync_tasks.get_nowait()
        task.execute()

        emitter.emit(PingEvent())
        # Once listener should have been removed, so no new task
        assert emitter._sync_executor._sync_tasks.empty()
        assert len(count) == 1
