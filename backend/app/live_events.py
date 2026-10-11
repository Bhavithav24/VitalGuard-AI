"""Authenticated WebSocket fan-out with optional shared Redis/Valkey Pub/Sub.

REST history remains the recovery path because Pub/Sub does not replay missed
messages. When REDIS_URL is configured, every backend instance publishes to the
shared channel and every instance forwards received events to its local clients.
Without it, the service safely falls back to single-process fan-out.
"""
from __future__ import annotations

import asyncio
import json
import os
from fastapi import WebSocket, WebSocketDisconnect

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover
    redis = None


class LiveEventHub:
    def __init__(self, send_timeout_seconds: float = 2.0) -> None:
        if send_timeout_seconds <= 0:
            raise ValueError("send_timeout_seconds must be positive")
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._send_timeout_seconds = send_timeout_seconds
        self._redis = None
        self._pubsub = None
        self._subscriber_task: asyncio.Task | None = None
        self.transport = "process_local_best_effort"

    async def start(self) -> None:
        url = os.getenv("REDIS_URL", "").strip()
        if not url or redis is None:
            return
        try:
            self._redis = redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
            await self._redis.ping()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe("vitalguard.events")
            self._subscriber_task = asyncio.create_task(self._listen_shared_events())
            self.transport = "redis_pubsub"
        except Exception:
            await self.stop()

    async def stop(self) -> None:
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
            self._subscriber_task = None
        if self._pubsub:
            try:
                await self._pubsub.close()
            except Exception:
                pass
            self._pubsub = None
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None
        self.transport = "process_local_best_effort"

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        await websocket.send_json({"type": "connected", "demo_only": True, "transport": self.transport})

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def _send_local(self, event: dict) -> None:
        async with self._lock:
            clients = list(self._clients)
        stale = []
        for client in clients:
            try:
                await asyncio.wait_for(client.send_json(event), timeout=self._send_timeout_seconds)
            except Exception:
                stale.append(client)
        if stale:
            async with self._lock:
                for client in stale:
                    self._clients.discard(client)

    async def _listen_shared_events(self) -> None:
        while self._pubsub:
            try:
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    event = json.loads(message["data"])
                    await self._send_local(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(1)

    async def broadcast(self, event: dict) -> None:
        if self._redis and self.transport == "redis_pubsub":
            try:
                await self._redis.publish("vitalguard.events", json.dumps(event, separators=(",", ":")))
                return
            except Exception:
                self.transport = "process_local_best_effort"
        await self._send_local(event)

    async def serve(self, websocket: WebSocket) -> None:
        await self.connect(websocket)
        try:
            while True:
                message = await websocket.receive_text()
                if message == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            await self.disconnect(websocket)
        except Exception:
            await self.disconnect(websocket)


hub = LiveEventHub()
