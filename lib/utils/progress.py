# -*- coding: utf-8 -*-
"""
进度条工具
提供简单的命令行进度条显示功能
"""

import sys
from typing import Optional, Callable, Any


class ProgressBar:
    """
    简单的命令行进度条

    使用示例：
        progress = ProgressBar(1000, "处理中")
        for i in range(1000):
            # ... 执行任务 ...
            progress.update(i + 1)
        progress.close()
    """

    # 进度条宽度（字符数）
    BAR_WIDTH = 40

    def __init__(self, total: int, prefix: str = "", suffix: str = ""):
        """
        初始化进度条

        Args:
            total: 总任务数
            prefix: 前缀文本
            suffix: 后缀文本
        """
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.current = 0
        self._last_percent = -1

        if total > 0:
            self._show_progress(0)

    def update(self, current: int) -> None:
        """
        更新进度

        Args:
            current: 当前进度
        """
        self.current = current
        if self.total > 0:
            percent = int(100 * current / self.total)
            if percent != self._last_percent:
                self._last_percent = percent
                self._show_progress(percent)

    def _show_progress(self, percent: int) -> None:
        """显示进度条"""
        # 计算填充长度
        filled = int(self.BAR_WIDTH * percent / 100)
        bar = '█' * filled + '░' * (self.BAR_WIDTH - filled)

        # 格式化输出
        if self.prefix:
            prefix_str = f"{self.prefix}: "
        else:
            prefix_str = ""

        # 构建进度行
        progress_line = f"\r{prefix_str}[{bar}] {percent:3d}%"

        if self.suffix:
            progress_line += f" {self.suffix}"

        # 清除行尾多余字符并输出
        sys.stdout.write(progress_line + " " * 10)
        sys.stdout.flush()

    def close(self) -> None:
        """完成进度条，换行"""
        if self.total > 0:
            self._show_progress(100)
            print()  # 换行


def show_progress(
    iterable,
    total: Optional[int] = None,
    prefix: str = "",
    suffix: str = ""
) -> Any:
    """
    带进度条的迭代器

    使用示例：
        for item in show_progress(items, prefix="处理中"):
            # ... 处理 item ...

    Args:
        iterable: 可迭代对象
        total: 总数（默认从 iterable 获取）
        prefix: 前缀文本
        suffix: 后缀文本

    Yields:
        迭代元素
    """
    if total is None:
        try:
            total = len(iterable)
        except TypeError:
            total = 0

    progress = ProgressBar(total, prefix, suffix)

    for i, item in enumerate(iterable):
        yield item
        progress.update(i + 1)

    progress.close()


def progress_range(
    total: int,
    prefix: str = "",
    suffix: str = ""
) -> range:
    """
    带进度条的 range

    使用示例：
        for i in progress_range(1000, prefix="处理中"):
            # ... 执行任务 ...

    Args:
        total: 总数
        prefix: 前缀文本
        suffix: 后缀文本

    Returns:
        range 对象（会显示进度）
    """
    return _ProgressRange(total, prefix, suffix)


class _ProgressRange:
    """带进度条的 range 包装器"""

    def __init__(self, total: int, prefix: str = "", suffix: str = ""):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self._progress: Optional[ProgressBar] = None

    def __iter__(self):
        self._progress = ProgressBar(self.total, self.prefix, self.suffix)
        for i in range(self.total):
            yield i
            self._progress.update(i + 1)
        self._progress.close()
