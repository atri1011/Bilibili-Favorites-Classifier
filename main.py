import sys
from pathlib import Path
import asyncio

# 将 src 目录添加到 Python 路径
# 这确保了我们可以从项目根目录运行脚本
# 也能找到 src 目录下的模块
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from cli import cli

def main():
    """程序主入口"""
    try:
        # Click 会自动处理 asyncio 事件循环
        cli()
    except KeyboardInterrupt:
        print("\n👋 用户取消操作。")
        sys.exit(0)
    except Exception as e:
        # 可以添加一些顶层的错误捕获
        print(f"发生未预料的错误: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()