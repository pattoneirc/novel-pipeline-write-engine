#!/usr/bin/env python3
"""
scene_delta_guard.py — 场景推进证据门禁

证明每个场景不是空转，而是在推进剧情。
把章节拆成场景，分析每个场景的 delta（推进了什么）。

用法:
  python scripts/scene_delta_guard.py content.txt \
    [--chapter-type normal] [--output report.json]
"""

import re, json, sys, argparse
from pathlib import Path


def split_scenes(content):
    """按时间/地点标记拆分场景"""
    paragraphs = [p.strip() for p in content.split("\n") if p.strip() and not p.startswith("=")]

    scene_boundaries = [0]  # start indices (paragraph numbers)
    boundary_markers = [
        r'^(第.{1,4}天|早上|傍晚|晚上|深夜|第二天|次日|清晨|黄昏|午后|下午|当天|不久之后|与此同时|另一边)',
        r'^(回到|来到|走进|出了|站在|蹲在|坐在|躺在|来到)',
        r'^(\*{3,}|-{3,}|#{1,3}\s)',
        r'^(……|\.{4,})',
    ]

    for i, p in enumerate(paragraphs[1:], 1):
        for marker in boundary_markers:
            if re.match(marker, p):
                scene_boundaries.append(i)
                break

    if len(scene_boundaries) < 2 or len(paragraphs) < 4:
        # 拆分不够 — 至少返回一个场景
        scene_boundaries = [0]

    scenes = []
    for j, start_idx in enumerate(scene_boundaries):
        end_idx = scene_boundaries[j+1] if j+1 < len(scene_boundaries) else len(paragraphs)
        scene_text = "\n".join(paragraphs[start_idx:end_idx])
        if len(scene_text.strip()) > 50:
            scenes.append({
                "scene_no": j + 1,
                "start_para": start_idx,
                "end_para": end_idx - 1,
                "text": scene_text
            })

    return scenes


def analyze_scene_delta(scene):
    """分析单个场景的推进量"""
    text = scene["text"]
    wc = len([c for c in text if '\u4e00' <= c <= '\u9fff'])

    delta = {
        "plot": "",
        "character_state": "",
        "relationship": "",
        "conflict": "",
        "worldbuilding": "",
        "reader_promise": "",
        "next_hook": ""
    }

    # plot 推进: 新动作/新事件
    if re.search(r'(发现|察觉|注意|看到|听到|找到|获得|失去|完成|失败|成功)', text):
        delta["plot"] = "新发现或事件推进"

    # character_state: 人物心理/状态变化
    if re.search(r'(决定|选择|放弃|坚持|改变|转变|动摇|坚定|犹豫)', text):
        delta["character_state"] = "人物状态变化"

    # relationship: 关系变化
    if re.search(r'(争吵|和解|合作|背叛|信任|怀疑|感激|怨恨)', text):
        delta["relationship"] = "关系互动或变化"

    # conflict: 冲突
    if re.search(r'(阻止|反对|对抗|冲突|矛盾|争执|较量|斗法|战斗|打斗)', text):
        delta["conflict"] = "冲突升级或解决"

    # worldbuilding: 世界观展开
    if re.search(r'(规则|法则|定律|原理|机制|体系|结构|本源|天道|灵力|灵气)', text):
        delta["worldbuilding"] = "世界观揭示或深化"

    # reader_promise: 读者承诺推进
    if re.search(r'(约定|承诺|答应|保证|誓言|一定会|必须|早晚有一天)', text):
        delta["reader_promise"] = "读者承诺推进"

    # next_hook: 留下钩子
    if re.search(r'(但.{0,20}(?:突然|忽然|竟然|却)|然而.{0,20}(?:发现|出现)|而.{0,10}(?:不知|还没|尚未))', text):
        delta["next_hook"] = "留下悬念或钩子"

    # 计算有效推进维度
    delta_count = sum(1 for v in delta.values() if v)

    return {
        "scene_no": scene["scene_no"],
        "scene_role": "场景",
        "word_count": wc,
        "delta": delta,
        "delta_count": delta_count,
        "scene_passed": delta_count >= 2
    }


def run_scene_delta_check(content, chapter_type="normal"):
    """主入口：运行场景推进检查"""

    scenes_data = split_scenes(content)
    if not scenes_data:
        return {
            "scenes": [],
            "effective_scene_delta_count": 0,
            "low_delta_scenes": [],
            "overall_passed": False,
            "error": "无法拆分场景"
        }

    analyzed_scenes = [analyze_scene_delta(s) for s in scenes_data]

    # 统计
    effective_delta_count = sum(s["delta_count"] for s in analyzed_scenes)
    low_delta = [s for s in analyzed_scenes if s["delta_count"] < 2]

    # 判定标准
    is_short = chapter_type in ("authorized_short", "fragment", "short")

    if is_short:
        min_delta = 1
        max_low = len(analyzed_scenes)
    else:
        min_delta = 3
        max_low = 1

    passed = (
        effective_delta_count >= min_delta
        and len(low_delta) <= max_low
    )

    report = {
        "scenes": analyzed_scenes,
        "effective_scene_delta_count": effective_delta_count,
        "low_delta_scenes": [s["scene_no"] for s in low_delta],
        "overall_passed": passed
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Scene Delta Guard")
    parser.add_argument("content_file", help="章节 TXT 文件")
    parser.add_argument("--chapter-type", default="normal",
                        choices=["normal", "climax", "final", "short", "authorized_short", "fragment"])
    parser.add_argument("--output", default=None, help="输出 report JSON 路径")
    args = parser.parse_args()

    content = Path(args.content_file).read_text(encoding="utf-8")
    report = run_scene_delta_check(content, args.chapter_type)

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[OK] report saved: {args.output}")

    if not report["overall_passed"]:
        print(f"\n[FAIL] Scene delta check failed")
        print(f"  effective_scene_delta_count: {report['effective_scene_delta_count']}")
        print(f"  low_delta_scenes: {report['low_delta_scenes']}")
        sys.exit(1)
    else:
        print(f"\n[OK] Scene delta check passed ({report['effective_scene_delta_count']} effective deltas)")


if __name__ == "__main__":
    main()
