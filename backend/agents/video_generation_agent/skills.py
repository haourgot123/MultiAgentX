from pathlib import Path
from typing import Any


SKILL_NAME = "remotion-best-practices"
CORE_RULES = (
    "sequencing",
    "timing",
    "compositions",
    "parameters",
    "images",
    "text-animations",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_remotion_skill_bundle() -> dict[str, Any]:
    skill_dir = _repo_root() / "skills" / SKILL_NAME
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        raise FileNotFoundError(f"Skill not found: {skill_file}")

    rules: dict[str, str] = {}
    for rule_name in CORE_RULES:
        rule_path = skill_dir / "rules" / f"{rule_name}.md"
        if rule_path.exists():
            rules[rule_name] = _read_text(rule_path)

    summary_sections = [
        f"Skill name: {SKILL_NAME}",
        f"Skill root: {skill_dir}",
        "Primary prompt:",
        _read_text(skill_file),
    ]

    for rule_name, rule_content in rules.items():
        summary_sections.extend(
            [
                "",
                f"Referenced rule: {rule_name}",
                rule_content,
            ]
        )

    return {
        "name": SKILL_NAME,
        "path": str(skill_dir),
        "prompt_path": str(skill_file),
        "rules": rules,
        "summary": "\n".join(summary_sections).strip(),
    }
