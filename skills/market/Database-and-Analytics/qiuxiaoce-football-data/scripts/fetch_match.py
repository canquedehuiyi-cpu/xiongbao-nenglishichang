#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询赛程或单场全景数据，不执行文本生成与分析。"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

BASE_URL = "https://www.qiuxiaoce.com/wp-json/abv2-creator/v1"
USER_AGENT = "QiuXiaoCe-Skill-Agent/2.5.0"

from local_store import LocalStore


def get_api_key(cli_key=None):
    """按命令参数、环境变量顺序读取 API Key。"""
    if cli_key:
        return cli_key.strip()
    return os.environ.get("QIUXIAOCE_API_KEY", "").strip() or None


def http_get(endpoint, key, params=None):
    """发送 GET 请求并返回解析后的 JSON。"""
    url = BASE_URL + endpoint
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "X-API-Key": key,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(body)
            message = payload.get("message", body)
        except (ValueError, TypeError):
            message = body
        return {"error": True, "status": error.code, "message": message}
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        return {"error": True, "message": str(error)}


def compact_pack(response):
    """在保留未知非空字段的前提下压缩 Match-Pack 响应。"""
    pack = response.get("pack")
    if not isinstance(pack, dict):
        return {"error": True, "message": "接口响应缺少有效的 pack 对象。"}

    preferred_keys = [
        "fixture_id", "league_id", "league_name", "kickoff", "venue_name",
        "referee", "home_team_id", "away_team_id", "home_name", "away_name",
        "fixture", "match", "teams", "league", "standings", "form",
        "recent_form", "home_form", "away_form", "home_stats", "away_stats",
        "injuries", "home_injuries", "away_injuries", "predicted_lineups",
        "lineups", "home_coach", "away_coach", "advanced", "home_advanced",
        "away_advanced", "team_advanced_metrics", "player_advanced_metrics",
        "calculated_metrics", "h2h", "coaches", "tactical", "injury_impact",
        "market_fluctuation", "market", "market_movements", "lottery_total_goals_odds", "_realtime_note",
    ]
    result = {
        "_summary": "球小策单场全景紧凑包；预测字段与衍生评分需单独标注，缺失字段不得补造。",
        "fixture_id": response.get("fixture_id"),
        "meta": response.get("meta") or {},
    }
    consumed = set()
    for key in preferred_keys:
        value = pack.get(key)
        if value not in (None, "", [], {}):
            result[key] = value
            consumed.add(key)

    other = {
        key: value for key, value in pack.items()
        if key not in consumed and value not in (None, "", [], {})
    }
    if other:
        result["other_non_empty_fields"] = other
    return result


def fixture_team_name(fixture, side):
    """兼容不同赛程字段结构并提取球队名。"""
    direct = fixture.get(f"{side}_team_name") or fixture.get(f"{side}_team")
    if isinstance(direct, str):
        return direct
    if isinstance(direct, dict):
        return str(direct.get("name") or "")
    teams = fixture.get("teams")
    if isinstance(teams, dict) and isinstance(teams.get(side), dict):
        return str(teams[side].get("name") or "")
    return ""


def main():
    """解析参数并执行赛程或 Match-Pack 查询。"""
    parser = argparse.ArgumentParser(description="球小策赛程定位与单场全景数据查询工具")
    parser.add_argument("--key", help="临时 API Key；优先推荐使用 QIUXIAOCE_API_KEY 环境变量")
    parser.add_argument("--date", help="比赛日期 YYYY-MM-DD，默认取本机当前日期")
    parser.add_argument("--team", help="用于筛选候选比赛的球队名称")
    parser.add_argument("--lottery-type", choices=["all", "zucai", "beidan"], default="all", help="赛程接口筛选参数")
    parser.add_argument("--pack", type=int, help="直接获取指定 fixture_id 的 Match-Pack")
    parser.add_argument("--task", type=int, help="查询指定 fixture_id 的完整包生成进度（0 点）")
    parser.add_argument("--raw", action="store_true", help="输出完整原始接口响应")
    args = parser.parse_args()

    key = get_api_key(args.key)
    if not key:
        print(json.dumps({
            "error": True,
            "message": "未检测到 API Key。请在本机安全设置 QIUXIAOCE_API_KEY 环境变量。",
        }, ensure_ascii=False))
        return 1

    if args.task:
        response = http_get(f"/tasks/{args.task}", key)
        if response.get("error"):
            print(json.dumps(response, ensure_ascii=False, indent=2))
            return 1
        response["_hint"] = (
            f"status=ready 时用 --pack {args.task} 获取完整包；"
            f"status=generating 时按 retry_after_seconds 等待后再查；"
            f"status=unknown 表示未触发过生成，请先执行 --pack {args.task}。"
        )
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0

    if args.pack:
        store = LocalStore()
        endpoint = f"/match-pack/{args.pack}"
        response = store.get(endpoint)
        source = "local"
        if response is None:
            response = http_get(endpoint, key)
            source = "api"
            if not response.get("error"):
                meta = response.get("meta") if isinstance(response.get("meta"), dict) else {}
                generation = meta.get("generation") if isinstance(meta.get("generation"), dict) else None
                if generation:
                    # 完整包尚未生成：不落本地缓存（避免半成品快照被反复命中），
                    # 把生成状态与快照一并透出，由上层 AI 引导用户等待后重取
                    snapshot = response if args.raw else compact_pack(response)
                    print(json.dumps({
                        "success": True,
                        "status": generation.get("status", "generating"),
                        "fixture_id": response.get("fixture_id"),
                        "task_id": generation.get("task_id"),
                        "status_url": generation.get("status_url"),
                        "eta_seconds": generation.get("eta_seconds"),
                        "retry_after_seconds": generation.get("retry_after_seconds", 30),
                        "credits_refunded": meta.get("credits_refunded", 0),
                        "message": generation.get("message"),
                        "_source": source,
                        "snapshot": snapshot,
                        "next_action": (
                            "该场次暂无完整数据包，系统已在后台生成。请直接告知用户："
                            "这场比赛的完整数据正在整理中，约 1 分钟后可再次查看，本次未扣点数。"
                            f"随后等待 retry_after_seconds 秒，重新执行 --pack {args.pack} 获取完整包；"
                            f"也可先执行 --task {args.pack} 查询进度（0 点）。"
                            "完整包就绪前，可先用 snapshot 里的基础维度作答，并说明其余维度稍后补全。"
                        ),
                    }, ensure_ascii=False, indent=2))
                    return 0
                store.set(endpoint, response)
                pack = response.get("pack") if isinstance(response.get("pack"), dict) else {}
                store.save_fixtures([pack], endpoint)
        if response.get("error"):
            print(json.dumps(response, ensure_ascii=False, indent=2))
            return 1
        output = response if args.raw else compact_pack(response)
        output["_source"] = source  # local 表示本地缓存命中，未扣点
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1 if output.get("error") else 0

    target_date = args.date or datetime.now().strftime("%Y-%m-%d")
    store = LocalStore()
    endpoint = "/fixtures"
    params = {"date": target_date, "lottery_type": args.lottery_type}
    response = store.get(endpoint, params)
    source = "local"
    if response is None:
        response = http_get(endpoint, key, params)
        source = "api"
        if isinstance(response, dict) and not response.get("error"):
            store.set(endpoint, response, params)
            store.save_fixtures(response.get("data") or [], endpoint)
    if response.get("error"):
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 1

    fixtures = response.get("data", []) if isinstance(response, dict) else []
    if not isinstance(fixtures, list):
        print(json.dumps({"error": True, "message": "赛程接口返回的 data 不是列表。"}, ensure_ascii=False))
        return 1

    if args.team:
        term = args.team.casefold().strip()
        fixtures = [
            fixture for fixture in fixtures
            if term in fixture_team_name(fixture, "home").casefold()
            or term in fixture_team_name(fixture, "away").casefold()
        ]

    print(json.dumps({
        "success": True,
        "date": response.get("date", target_date),
        "count": len(fixtures),
        "fixtures": fixtures,
        "_source": source,  # local 表示本地缓存命中，未扣点
        "note": "球队名称仅用于筛选候选项，后续查询必须使用 fixture_id。",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
