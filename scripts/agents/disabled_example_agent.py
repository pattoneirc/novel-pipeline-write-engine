"""
disabled_example_agent.py — Agent 子类示例（默认关闭）

此文件是一个可运行的示例模板，展示如何继承 BaseAgent 创建新 Agent。
默认 `enabled = False`，因此不会影响现有审稿流程。

如需启用，在 configs/agents.yaml 中配置即可。
如需创建新 Agent，直接复制此文件为模板。
"""

from .base_agent import BaseAgent


class ExampleAgent(BaseAgent):
    """示例 Agent — 展示 BaseAgent 子类的标准接口。"""

    def __init__(self):
        super().__init__(name="example_agent")

    def review(self, content: str, context: dict = None) -> dict:
        """审稿入口 — 替换下面占位逻辑为实际审稿代码。"""
        if not self.enabled:
            return super().review(content, context)
        # TODO: 在此添加实际的审稿逻辑，例如：
        #   from scripts.some_guard import run_check
        #   findings = run_check(content, context)
        #   return {"status": "PASS" if not findings else "WARN", "findings": findings}
        return {"status": "PASS", "findings": []}
