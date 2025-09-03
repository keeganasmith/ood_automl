# sessions.py
from __future__ import annotations
import copy
from typing import Any, Dict, Awaitable, Callable, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import uuid
import logging
import threading
import contextlib
from helper import load_table
from contextlib import redirect_stdout, redirect_stderr
from autogluon_log_parser import parse_autogluon_log
import sys
import time
from Base_Session import BaseSession
SUCCESS_MESSAGE = {"status": "success"}
# =========================
# ModifyDatasetSession (stubs)
# =========================

class ModifyDatasetSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.cursor = 0
        self.undo_stack = []
        self.df = None  # lazy-loaded

    async def dispatch(self, msg: Dict[str, Any]) -> Dict[str, Any]: ...
    async def load_dataset(self, path: str) -> Dict[str, Any]: ...
    async def view_rows(self, start: int, limit: int) -> Dict[str, Any]: ...
    async def view_problematic_rows(self, limit: int) -> Dict[str, Any]: ...
    async def change_rows(self, rows: list[dict]) -> Dict[str, Any]: ...
    async def replace_value(self, column: str, old: Any, new: Any, scope: str, row_indices=None) -> Dict[str, Any]: ...
    async def delete_columns(self, columns: list[str]) -> Dict[str, Any]: ...
    async def delete_rows(self, row_indices: list[int]) -> Dict[str, Any]: ...
    async def undo(self) -> Dict[str, Any]: ...
    async def save(self, path: str, overwrite: bool) -> Dict[str, Any]: ...
    async def coerce_type(self, column: str, to: str) -> Dict[str, Any]: ...
