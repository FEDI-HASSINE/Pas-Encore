from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _split_fields(line: str) -> list[str]:
    """
    Accept whitespace-separated or semicolon-separated fields.
    """
    return line.replace(";", " ").split()


def _find_section(lines: list[str], section_name: str) -> int:
    section_name = section_name.lower()

    for i, line in enumerate(lines):
        if section_name in line.lower():
            return i

    raise ValueError(
        f"Section '{section_name}' not found"
    )


def load_psplib(path: str | Path) -> list[dict[str, Any]]:
    """
    Load one PSPLIB instance.

    Returns only the 30 real tasks (supersource and supersink
    are excluded).

    Returned schema:

        {
            "id": int,
            "duration": int,
            "predecessors": list[int],
            "resources": list[int]
        }
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"PSPLIB file not found: {path}"
        )

    content = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    if "\x00" in content:
        logger.warning("Null bytes detected in %s", path)
        content = content.replace("\x00", "")

    lines = content.splitlines()

    # =========================================================
    # 1. PRECEDENCE RELATIONS
    # =========================================================

    precedence_idx = _find_section(
        lines,
        "PRECEDENCE RELATIONS"
    )

    predecessors: dict[int, list[int]] = {}

    i = precedence_idx + 1

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        if "REQUESTS/DURATIONS" in line.upper():
            break

        parts = _split_fields(line)

        # Logical format:
        # job_id  mode  number_of_successors  successor_1 ...
        if parts and parts[0].isdigit() and len(parts) >= 4:
            job_id = int(parts[0])
            number_successors = int(parts[2])

            successors = [
                int(x)
                for x in parts[3:3 + number_successors]
            ]

            predecessors.setdefault(job_id, [])

            for successor in successors:
                predecessors.setdefault(successor, [])
                predecessors[successor].append(job_id)

        i += 1

    # =========================================================
    # 2. REQUESTS / DURATIONS
    # =========================================================

    requests_idx = _find_section(
        lines,
        "REQUESTS/DURATIONS"
    )

    tasks: dict[int, dict[str, Any]] = {}

    i = requests_idx + 1

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        if "RESOURCEAVAILABILITIES" in line.upper() or line.startswith("****"):
            break

        parts = _split_fields(line)

        # Logical format:
        # job_id mode duration resource_1 resource_2 ...
        if parts and parts[0].isdigit() and len(parts) >= 4:
            job_id = int(parts[0])
            mode = int(parts[1])
            duration = int(parts[2])

            # Week 1 uses a single-mode instance.
            if mode == 1:
                resources = [
                    int(x)
                    for x in parts[3:]
                ]

                tasks[job_id] = {
                    "id": job_id,
                    "duration": duration,
                    "predecessors": sorted(
                        predecessors.get(job_id, [])
                    ),
                    "resources": resources,
                }

        i += 1

    # =========================================================
    # 3. FILTER OUT SUPERSOURCE / SUPERSINK
    # =========================================================
    # Supersource (job 1) and supersink (last job) have
    # duration == 0 and resources == all zeros. They are
    # PSPLIB structural dummies, not real schedulable tasks.

    real_tasks = [
        t for t in tasks.values()
        if t["duration"] > 0 or t["resources"] != [0] * len(t["resources"])
    ]

    return sorted(real_tasks, key=lambda t: t["id"])


def load_all_psplib(
    directory: str | Path,
) -> dict[str, list[dict[str, Any]]]:
    """
    Load all PSPLIB .sm instances from a directory.

    Returns a dictionary mapping each filename to its
    parsed task list (30 real tasks per instance).

        {
            "j3010_1.sm": [
                {"id": 2, "duration": 2, ...},
                ...
            ],
            "j3010_2.sm": [...],
            ...
        }
    """
    directory = Path(directory)

    if not directory.is_dir():
        raise NotADirectoryError(
            f"Directory not found: {directory}"
        )

    sm_files = sorted(directory.glob("*.sm"))

    if not sm_files:
        raise FileNotFoundError(
            f"No .sm files found in: {directory}"
        )

    return {
        f.name: load_psplib(f)
        for f in sm_files
    }
