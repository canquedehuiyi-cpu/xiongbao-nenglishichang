from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]


def read(rel_path: str) -> str:
    return (SKILL_ROOT / rel_path).read_text(encoding="utf-8")


def test_required_skill_files_exist():
    for rel_path in [
        "info.json",
        "meta.json",
        "SKILL.md",
        "requirements.txt",
        "scripts/client.py",
        "scripts/server.py",
        "scripts/run.ps1",
        "scripts/yolo_demo.py",
        "scripts/demo_utils.py",
        "scripts/ensure_models.py",
        "tests/test_structure.py",
    ]:
        assert (SKILL_ROOT / rel_path).exists(), rel_path


def test_no_aipc_check_in_run_ps1():
    run_ps1 = read("scripts/run.ps1")
    assert "is-aipc" not in run_ps1
    assert "platform.exe" not in run_ps1


def test_info_json_no_timeout_and_venv():
    import json
    info = json.loads(read("info.json"))
    assert info["venv_name"] == "yolo26"
    assert info["server_alive_timeout"] == -1
    assert any("yolo26s.pt" in d["url"] for d in info["downloads"])
    assert any("coco8.zip" in d["url"] for d in info["downloads"])


def test_skill_md_has_bilingual_triggers():
    skill = read("SKILL.md")
    assert "目标检测" in skill
    assert "object detection" in skill.lower()
    assert "name: local-yolo26" in skill
