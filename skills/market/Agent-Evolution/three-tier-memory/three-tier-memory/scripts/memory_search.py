#!/usr/bin/env python3
"""
三层记忆系统 - 搜索工具

用法:
    python memory_search.py "数据库"
    python memory_search.py "EvoMap" --type evolution
    python memory_search.py "错误" --days 7
"""

import argparse
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", Path.home() / ".openclaw" / "workspace"))
MEMORY_DIR = WORKSPACE / "memory"
DB_PATH = MEMORY_DIR / "events.db"
DAILY_DIR = MEMORY_DIR / "daily"


def search_memory(query: str, event_type: str = None, days: int = 30, limit: int = 20) -> list:
    """搜索记忆系统"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sql = """
        SELECT id, type, content, importance, created_at
        FROM events
        WHERE content LIKE ?
        AND created_at >= datetime('now', ?)
    """
    params = [f"%{query}%", f"-{days} days"]

    if event_type:
        sql += " AND type = ?"
        params.append(event_type)

    sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    results = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "type": row[1],
            "content": row[2],
            "importance": row[3],
            "created_at": row[4]
        }
        for row in results
    ]


def search_daily_files(query: str, days: int = 7) -> list:
    """搜索每日日记文件"""

    results = []
    today = datetime.now()

    for i in range(days):
        date = today - timedelta(days=i)
        daily_file = DAILY_DIR / f"{date.strftime('%Y-%m-%d')}.md"

        if daily_file.exists():
            with open(daily_file, "r", encoding="utf-8") as f:
                content = f.read()

            if query.lower() in content.lower():
                results.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "file": str(daily_file),
                    "matches": content.count(query)
                })

    return results


def main():
    parser = argparse.ArgumentParser(description="搜索三层记忆系统")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--type", "-t", choices=["decision", "insight", "task", "error", "evolution"],
                        help="事件类型过滤")
    parser.add_argument("--days", "-d", type=int, default=30,
                        help="搜索天数 (默认 30)")
    parser.add_argument("--limit", "-l", type=int, default=20,
                        help="结果数量限制 (默认 20)")

    args = parser.parse_args()

    # 搜索事件数据库
    events = search_memory(args.query, args.type, args.days, args.limit)

    # 搜索每日日记
    daily_matches = search_daily_files(args.query, min(args.days, 7))

    print(f"🔍 搜索: \"{args.query}\"")
    print()

    if events:
        print("📋 事件记录:")
        for e in events:
            stars = "⭐" * e["importance"]
            time = e["created_at"].split("T")[1][:5] if "T" in e["created_at"] else ""
            print(f"  [{e['type'].upper()}] {stars} {e['content'][:60]}...")
            print(f"    时间: {e['created_at'][:10]} {time}")
        print()

    if daily_matches:
        print("📅 每日日记:")
        for d in daily_matches:
            print(f"  {d['date']} - {d['matches']} 处匹配")
        print()

    if not events and not daily_matches:
        print("未找到匹配结果")


if __name__ == "__main__":
    main()
