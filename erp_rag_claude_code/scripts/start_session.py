#!/usr/bin/env python3
"""
start_session.py — ChronicCare Backend
Run this at the start of every Claude Code session.

Usage:
    python scripts/start_session.py
    python scripts/start_session.py --role executor
    python scripts/start_session.py --sprint 2
"""

from __future__ import annotations
import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
SPRINTS_DIR = ROOT / "sprints"
MEMORY_DIR = ROOT / "memory"
AGENTS_DIR = ROOT / "agents"

# ANSI colours
R = "\033[0;31m"
G = "\033[0;32m"
Y = "\033[0;33m"
B = "\033[0;34m"
C = "\033[0;36m"
W = "\033[1;37m"
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"


def header(text: str) -> None:
    width = 60
    print(f"\n{B}{'─' * width}{RESET}")
    print(f"{BOLD}{W}  {text}{RESET}")
    print(f"{B}{'─' * width}{RESET}")


def ok(msg: str) -> None:
    print(f"  {G}✓{RESET}  {msg}")


def warn(msg: str) -> None:
    print(f"  {Y}⚠{RESET}  {msg}")


def error(msg: str) -> None:
    print(f"  {R}✗{RESET}  {msg}")


def info(msg: str) -> None:
    print(f"  {DIM}→{RESET}  {msg}")


# ─── Git checks ──────────────────────────────────────────────────────────────

def check_git() -> dict:
    result = {}

    # Current branch
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ROOT, text=True
        ).strip()
        result["branch"] = branch
    except subprocess.CalledProcessError:
        result["branch"] = "unknown"

    # Dirty working tree
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=ROOT, text=True
        ).strip()
        result["dirty"] = bool(status)
        result["dirty_files"] = status.splitlines()
    except subprocess.CalledProcessError:
        result["dirty"] = False
        result["dirty_files"] = []

    # Latest commit
    try:
        commit = subprocess.check_output(
            ["git", "log", "--oneline", "-1"],
            cwd=ROOT, text=True
        ).strip()
        result["last_commit"] = commit
    except subprocess.CalledProcessError:
        result["last_commit"] = "n/a"

    return result


def print_git_status(git: dict) -> None:
    header("Git Status")
    branch = git["branch"]

    if branch in ("main", "develop"):
        warn(f"You are on '{branch}'. Do NOT commit directly here.")
        info("Create a feature branch: git checkout -b feature/BE-<id>-<slug>")
    elif branch.startswith("feature/") or branch.startswith("fix/"):
        ok(f"Branch: {branch}")
    else:
        warn(f"Unusual branch name: {branch}. Expected feature/BE-<id>-... or fix/BE-<id>-...")

    if git["dirty"]:
        warn("Working tree is dirty:")
        for f in git["dirty_files"][:10]:
            info(f)
        if len(git["dirty_files"]) > 10:
            info(f"... and {len(git['dirty_files']) - 10} more")
    else:
        ok("Working tree is clean")

    info(f"Last commit: {git['last_commit']}")


# ─── Environment checks ───────────────────────────────────────────────────────

def check_env() -> dict:
    env_file = ROOT / ".env"
    env_example = ROOT / ".env.example"

    required_keys = [
        "GEMINI_API_KEY",
        "FIREBASE_CREDENTIALS_PATH",
        "REDIS_URL",
        "SENDGRID_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "DEMO_PATIENT_ID",
    ]

    result = {
        "env_exists": env_file.exists(),
        "missing_keys": [],
        "present_keys": [],
    }

    if env_file.exists():
        content = env_file.read_text()
        for key in required_keys:
            if key in content and f"{key}=" in content:
                # Check it's not empty
                for line in content.splitlines():
                    if line.startswith(f"{key}="):
                        value = line.split("=", 1)[1].strip()
                        if value:
                            result["present_keys"].append(key)
                        else:
                            result["missing_keys"].append(f"{key} (empty)")
                        break
            else:
                result["missing_keys"].append(key)

    return result


def print_env_status(env: dict) -> None:
    header("Environment")
    if not env["env_exists"]:
        error(".env file not found!")
        info("Run: cp .env.example .env  then fill in your credentials")
        return

    ok(".env file exists")

    if env["missing_keys"]:
        warn("Missing or empty keys:")
        for k in env["missing_keys"]:
            info(k)
    else:
        ok(f"All {len(env['present_keys'])} required keys are set")


# ─── Sprint status ────────────────────────────────────────────────────────────

def detect_current_sprint() -> int:
    """Return the sprint number with the most recent open P0 tickets."""
    sprint_files = sorted(SPRINTS_DIR.glob("sprint*.md"))
    if not sprint_files:
        return 1

    for sprint_file in reversed(sprint_files):
        content = sprint_file.read_text()
        if "🔲" in content or "[ ]" in content:
            # Extract sprint number from filename
            name = sprint_file.stem  # e.g. "sprint2"
            try:
                return int("".join(filter(str.isdigit, name)))
            except ValueError:
                pass

    return len(sprint_files)


def parse_sprint_tickets(sprint_num: int) -> list[dict]:
    sprint_file = SPRINTS_DIR / f"sprint{sprint_num}.md"
    if not sprint_file.exists():
        return []

    tickets = []
    content = sprint_file.read_text()
    lines = content.splitlines()

    current = {}
    for line in lines:
        if line.startswith("### BE-"):
            if current:
                tickets.append(current)
            # Parse: ### BE-08: Title
            parts = line.lstrip("# ").split(":", 1)
            ticket_id = parts[0].strip()
            title = parts[1].strip() if len(parts) > 1 else ""
            current = {"id": ticket_id, "title": title, "priority": "?", "status": "🔲"}
        elif "**Priority:**" in line:
            current["priority"] = line.split("**Priority:**")[1].strip()
        elif "**Status:**" in line:
            current["status"] = line.split("**Status:**")[1].strip()
        elif line.strip().startswith("- [x]") or line.strip().startswith("- [X]"):
            current["status"] = "✅"

    if current:
        tickets.append(current)

    return tickets


def print_sprint_status(sprint_num: int) -> None:
    header(f"Sprint {sprint_num} — Ticket Status")
    tickets = parse_sprint_tickets(sprint_num)

    if not tickets:
        warn(f"No sprint{sprint_num}.md found in sprints/")
        info("Run the Planner agent to generate sprint tickets.")
        return

    p0_open = [t for t in tickets if "P0" in t["priority"] and "✅" not in t["status"]]
    p0_done = [t for t in tickets if "P0" in t["priority"] and "✅" in t["status"]]
    p1 = [t for t in tickets if "P1" in t["priority"]]
    p2 = [t for t in tickets if "P2" in t["priority"]]

    if p0_open:
        error(f"{len(p0_open)} P0 ticket(s) still open:")
        for t in p0_open:
            info(f"  {R}{t['id']}{RESET} {t['title']}")
        warn("Complete all P0 tickets before starting P2 work.")
    else:
        ok(f"All {len(p0_done)} P0 tickets complete — exit gate ready to validate!")

    if p1:
        p1_done = [t for t in p1 if "✅" in t["status"]]
        print(f"\n  {C}P1:{RESET} {len(p1_done)}/{len(p1)} done")

    if p2:
        p2_done = [t for t in p2 if "✅" in t["status"]]
        print(f"  {C}P2:{RESET} {len(p2_done)}/{len(p2)} done")

    total_done = sum(1 for t in tickets if "✅" in t["status"])
    print(f"\n  {BOLD}Total:{RESET} {total_done}/{len(tickets)} tickets complete\n")


# ─── Memory feedback ─────────────────────────────────────────────────────────

def print_memory_summary() -> None:
    header("Active Memory Feedback")
    memory_index = MEMORY_DIR / "MEMORY.md"
    if not memory_index.exists():
        warn("memory/MEMORY.md not found")
        return

    content = memory_index.read_text()
    # Extract the table rows from Active Feedback section
    in_table = False
    rows_found = 0
    for line in content.splitlines():
        if "Active Feedback" in line:
            in_table = True
            continue
        if in_table and line.startswith("| `feedback_"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 4:
                file_name = parts[0].strip("`")
                severity = parts[2]
                summary = parts[3]
                sev_color = R if "Critical" in severity else Y if "Warning" in severity else C
                print(f"  {sev_color}{severity}{RESET}  {DIM}{file_name}{RESET}")
                print(f"        {summary}")
                rows_found += 1
        if in_table and line.startswith("## Resolved"):
            break

    if rows_found == 0:
        ok("No active feedback warnings")
    else:
        info(f"Read memory/ files for details before starting your task.")


# ─── Agent role ───────────────────────────────────────────────────────────────

def print_role_instructions(role: str | None) -> None:
    header("Agent Role")
    roles = {
        "planner": ("agents/planner.md", "Decompose sprint objectives into tickets"),
        "executor": ("agents/executor.md", "Implement a single ticket"),
        "tester": ("agents/tester.md", "Write and run tests for a ticket"),
        "committer": ("agents/committer.md", "Stage, commit, and open PR"),
    }

    if role and role.lower() in roles:
        file_path, description = roles[role.lower()]
        ok(f"Role: {BOLD}{role.upper()}{RESET}")
        info(f"{description}")
        info(f"Read your role definition: {file_path}")
    else:
        print(f"  Available roles:")
        for r, (path, desc) in roles.items():
            print(f"    {C}{r:12}{RESET} {desc}")
        info("Set your role: python scripts/start_session.py --role <role>")


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Start a ChronicCare backend session")
    parser.add_argument("--role", choices=["planner", "executor", "tester", "committer"],
                        help="Agent role for this session")
    parser.add_argument("--sprint", type=int, help="Override sprint number detection")
    args = parser.parse_args()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{BOLD}{W}ChronicCare (Nour) — Session Start  {DIM}{now}{RESET}")

    git = check_git()
    print_git_status(git)

    env = check_env()
    print_env_status(env)

    sprint_num = args.sprint or detect_current_sprint()
    print_sprint_status(sprint_num)

    print_memory_summary()

    print_role_instructions(args.role)

    header("Ready")
    if git["branch"] not in ("main", "develop") and not env["missing_keys"]:
        ok("Environment looks good. Start coding!")
    else:
        warn("Fix the issues above before writing code.")

    print(f"\n{DIM}  Docs: CLAUDE.md · BEST_PRACTICES.md · agents/{args.role or '<role>'}.md{RESET}\n")


if __name__ == "__main__":
    main()