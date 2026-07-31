"""结构化日志（JSON 友好的控制台输出）。"""
from __future__ import annotations

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":"%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # 降低第三方库噪音
    for noisy in ("httpx", "httpcore", "chromadb", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


setup_logging()
