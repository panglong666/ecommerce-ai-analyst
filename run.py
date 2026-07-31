"""一键启动 FastAPI 服务。PyCharm 中右键 Run 即可。"""
import os
import sys
import webbrowser
import threading

import uvicorn

from ecommerce_ai.core.config import settings


def open_browser(host: str, port: int) -> None:
    url = f"http://{host}:{port}"
    # 延迟打开，等服务起来
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()


def main() -> None:
    host = settings.host
    port = settings.port
    print(f"\n  电商数据分析 AI 应用启动中...")
    print(f"  访问地址: http://{host}:{port}")
    print(f"  数据源: {settings.data_source} | 大模型: {settings.llm_provider}"
          + ("" if settings.deepseek_api_key else " (未填 Key，使用 MockLLM 回退)")
          + "\n")
    open_browser(host, port)
    uvicorn.run("ecommerce_ai.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
