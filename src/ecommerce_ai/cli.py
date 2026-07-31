"""命令行入口：python -m ecommerce_ai "问题"  或  --serve。"""
from __future__ import annotations

import sys

from ecommerce_ai.core.config import settings


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("用法:")
        print('  python -m ecommerce_ai "上个月华东区羽绒服销售额"')
        print("  python -m ecommerce_ai --serve   # 启动 Web 服务")
        return

    if args[0] == "--serve":
        import uvicorn

        uvicorn.run("ecommerce_ai.api.app:app", host=settings.host, port=settings.port)
        return

    question = " ".join(args)
    from ecommerce_ai.agents.graph import run

    resp = run(question)
    print("\n" + "=" * 60)
    print(f"问题: {resp.question}")
    print(f"路由: {resp.route}  耗时: {resp.elapsed_ms}ms")
    if resp.sql:
        print(f"SQL:  {resp.sql}")
    if resp.rows:
        print(f"结果: {len(resp.rows)} 行  列: {resp.columns}")
    if resp.sources:
        print(f"来源: {resp.sources}")
    print("-" * 60)
    print(resp.answer)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
