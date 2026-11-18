#!/usr/bin/env python3
"""
三层记忆系统 - 事件添加工具

用法:
    python memory_add.py decision "选择使用 PostgreSQL 作为主数据库"
    python memory_add.py insight "学会了 EvoMap A2A 协议" --importance 4
    python memory_add.py error "修复了 API 超时问题" --capsule
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", Path.home() / ".openclaw" / "workspace"))
MEMORY_DIR = WORKSPACE / "memory"
DB_PATH = MEMORY_DIR / "events.db"
DAILY_DIR = MEMORY_DIR / "daily"


def add_event(event_type: str, content: str, importance: int = 3, capsule: bool = False) -> dict:
    """添加事件到记忆系统"""

    # 确保 L2 目录存在
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    # 写入事件数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO events (type, content, importance) VALUES (?, ?, ?)",
        (event_type, content, importance)
    )
    event_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # 写入今日日记
    today = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M")
    daily_file = DAILY_DIR / f"{today}.md"

    importance_marker = "⭐" * min(importance, 5)
    entry = f"- {time_str} [{event_type.upper()}] {importance_marker} {content}\n"

    with open(daily_file, "a", encoding="utf-8") as f:
        f.write(entry)

    # 更新 recent-events.md
    recent_file = MEMORY_DIR / "recent-events.md"
    with open(recent_file, "a", encoding="utf-8") as f:
        f.write(entry)

    result = {
        "event_id": event_id,
        "type": event_type,
        "content": content,
        "importance": importance,
        "daily_file": str(daily_file)
    }

    # 如果是高重要性且有 capsule 标志，创建 Capsule 模板
    if capsule and importance >= 4:
        capsule_dir = WORKSPACE / "capsules"
        capsule_dir.mkdir(parents=True, exist_ok=True)

        capsule_template = {
            "type": "Capsule",
            "schema_version": "1.5.0",
            "trigger": [],
            "summary": content,
            "content": f"待补充详细内容...\n\n事件 ID: {event_id}\n时间: {datetime.now().isoformat()}",
            "confidence": 0.8,
            "blast_radius": {"files": 0, "lines": 0},
            "outcome": {"status": "success", "score": 0.8},
            "env_fingerprint": {"platform": "linux", "arch": "x64"}
        }

        capsule_file = capsule_dir / f"event-{event_id}.json"
        with open(capsule_file, "w", encoding="utf-8") as f:
            json.dump(capsule_template, f, indent=2, ensure_ascii=False)

        result["capsule_file"] = str(capsule_file)

    return result


def main():
    parser = argparse.ArgumentParser(description="添加事件到三层记忆系统")
    parser.add_argument("type", choices=["decision", "insight", "task", "error", "evolution"],
                        help="事件类型")
    parser.add_argument("content", help="事件内容")
    parser.add_argument("--importance", "-i", type=int, default=3, choices=range(1, 6),
                        help="重要性 (1-5, 默认 3)")
    parser.add_argument("--capsule", "-c", action="store_true",
                        help="创建 Capsule 模板")

    args = parser.parse_args()

    result = add_event(args.type, args.content, args.importance, args.capsule)

    print(f"✅ 事件已添加")
    print(f"   ID: {result['event_id']}")
    print(f"   类型: {result['type']}")
    print(f"   重要性: {'⭐' * result['importance']}")

    if "capsule_file" in result:
        print(f"   Capsule 模板: {result['capsule_file']}")


if __name__ == "__main__":
    main()
