from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from .instances import ArtifactFile, BenchmarkInstance, normalize_relative_path

DATASET_ROOT = Path(__file__).resolve().parent.parent / "dataset"
TEXT_SUFFIXES = {".csv", ".md", ".py", ".txt", ".yaml", ".yml"}
RELEASE_DIFFICULTIES = {"easy", "medium", "hard"}


class Benchmark:
    """Released MM-OptBench catalog and artifact access."""

    def problems(
        self,
        *,
        family: str | None = None,
        problem: str | None = None,
        difficulty: str | None = None,
        paths: Sequence[str] | None = None,
    ) -> tuple[dict[str, object], ...]:
        """Return released problem records with their included instances."""
        path_filters = tuple(_normalize_selector_path(path) for path in (paths or ()))
        records: list[dict[str, object]] = []
        for directory in sorted(DATASET_ROOT.glob("*/*/*")):
            if not directory.is_dir():
                continue
            record_family, record_problem, record_difficulty = directory.relative_to(DATASET_ROOT).parts
            if record_difficulty not in RELEASE_DIFFICULTIES:
                continue
            if family is not None and family != record_family:
                continue
            if problem is not None and problem != record_problem:
                continue
            if difficulty is not None and difficulty != record_difficulty:
                continue
            record_path = (record_family, record_problem, record_difficulty)
            if path_filters and not any(record_path[:len(path)] == path for path in path_filters):
                continue
            released_instances = tuple(
                task_input.parent.name
                for task_input in sorted(directory.glob("*/task_input.txt"))
                if (task_input.parent / "ground_truth" / "instance_data.json").is_file()
            )
            if not released_instances:
                continue
            instance_keys = tuple(
                f"{record_family}/{record_problem}/{record_difficulty}/{instance_id}"
                for instance_id in released_instances
            )
            records.append(
                {
                    "family": record_family,
                    "problem": record_problem,
                    "difficulty": record_difficulty,
                    "instance_count": len(released_instances),
                    "released_instances": released_instances,
                    "instance_keys": instance_keys,
                }
            )
        return tuple(records)

    def instance_keys(
        self,
        *,
        family: str | None = None,
        problem: str | None = None,
        difficulty: str | None = None,
        paths: Sequence[str] | None = None,
        max_instances: int | None = None,
    ) -> tuple[str, ...]:
        """Return released instance keys matching the selected benchmark slice."""
        keys: list[str] = []
        for record in self.problems(family=family, problem=problem, difficulty=difficulty, paths=paths):
            keys.extend(str(key) for key in record["instance_keys"])
            if max_instances is not None and len(keys) >= max_instances:
                return tuple(keys[:max_instances])
        return tuple(keys)

    def instances(
        self,
        *,
        family: str | None = None,
        problem: str | None = None,
        difficulty: str | None = None,
        paths: Sequence[str] | None = None,
        instance: str | None = None,
        instance_id: str | None = None,
        max_instances: int | None = None,
    ) -> tuple[BenchmarkInstance, ...]:
        """Return released benchmark instances matching the selected slice."""
        if instance is not None:
            family, problem, difficulty, instance_id = parse_instance_key(instance)
        selected: list[BenchmarkInstance] = []
        local = ArtifactBenchmark()
        for key in self.instance_keys(family=family, problem=problem, difficulty=difficulty, paths=paths):
            if instance_id is not None and key.rsplit("/", 1)[-1] != instance_id:
                continue
            released = local.instance_from_dir(DATASET_ROOT / key)
            selected.append(replace(released, origin="mmopt_release"))
            if max_instances is not None and len(selected) >= max_instances:
                break
        return tuple(selected)

    def instance(self, instance_key: str) -> BenchmarkInstance:
        """Return one released benchmark instance by key."""
        instances = self.instances(instance=instance_key)
        if not instances:
            raise KeyError(f"Released instance not found: {instance_key}")
        return instances[0]


class ArtifactBenchmark:
    """Local exported or generated benchmark artifacts."""

    def instances(
        self,
        *,
        family_dir: str | Path | None = None,
        instance_dir: str | Path | None = None,
        family: str | None = None,
        difficulty: str | None = None,
        problem: str | None = None,
        max_instances: int | None = None,
    ) -> tuple[BenchmarkInstance, ...]:
        """Return local artifact instances matching the selected slice."""
        if instance_dir is not None:
            return (
                self.instance_from_dir(
                    instance_dir,
                    family=family,
                    problem=problem,
                    difficulty=difficulty,
                ),
            )
        if family_dir is None:
            raise ValueError("Either family_dir or instance_dir is required.")

        root = Path(family_dir).expanduser().resolve()
        instances: list[BenchmarkInstance] = []
        difficulty_names = [difficulty] if difficulty is not None else sorted(RELEASE_DIFFICULTIES)
        for difficulty_name in difficulty_names:
            if difficulty_name not in RELEASE_DIFFICULTIES:
                continue
            for task_input in sorted(root.glob(f"*/{difficulty_name}/*/task_input.txt")):
                candidate = task_input.parent
                if problem is not None and candidate.parent.parent.name != problem:
                    continue
                if not (candidate / "ground_truth" / "instance_data.json").is_file():
                    continue
                if not (candidate / "visuals").is_dir():
                    continue
                instances.append(self.instance_from_dir(candidate, family_root=root))
                if max_instances is not None and len(instances) >= max_instances:
                    return tuple(instances)
        return tuple(instances)

    def instance_from_dir(
        self,
        instance_dir: str | Path,
        *,
        family_root: str | Path | None = None,
        family: str | None = None,
        problem: str | None = None,
        difficulty: str | None = None,
    ) -> BenchmarkInstance:
        """Return one local artifact instance from an instance directory."""
        path = Path(instance_dir).expanduser().resolve()
        if not (path / "task_input.txt").is_file():
            raise FileNotFoundError(f"Missing task_input.txt in {path}")
        if family_root is not None:
            root = Path(family_root).expanduser().resolve()
            rel_parts = path.relative_to(root).parts
            resolved_family = family or root.name
            resolved_problem = problem or (rel_parts[0] if len(rel_parts) >= 3 else "unknown")
            resolved_difficulty = difficulty or (rel_parts[1] if len(rel_parts) >= 3 else "unknown")
        else:
            resolved_family = family or (path.parent.parent.parent.name if len(path.parents) >= 3 else "unknown")
            resolved_problem = problem or (path.parent.parent.name if len(path.parents) >= 2 else "unknown")
            resolved_difficulty = difficulty or (path.parent.name if len(path.parents) >= 1 else "unknown")
        if resolved_difficulty not in RELEASE_DIFFICULTIES:
            raise ValueError(
                f"Local artifact instances must be under one of {sorted(RELEASE_DIFFICULTIES)}; "
                f"got {resolved_difficulty!r} for {path}."
            )
        files = tuple(_artifact_from_path(file_path, path) for file_path in sorted(path.rglob("*")) if file_path.is_file())
        return BenchmarkInstance(
            family=resolved_family,
            problem=resolved_problem,
            difficulty=resolved_difficulty,
            instance_id=path.name,
            files=files,
            origin="local",
            source_dir=str(path),
        )


def parse_instance_key(instance: str) -> tuple[str, str, str, str]:
    parts = [part for part in instance.strip("/").split("/") if part]
    if len(parts) != 4:
        raise ValueError("Instance keys must have form family/problem/difficulty/instance_id.")
    return parts[0], parts[1], parts[2], parts[3]


def _normalize_selector_path(path: str) -> tuple[str, ...]:
    parts = tuple(part for part in path.strip("/").split("/") if part)
    if not 1 <= len(parts) <= 3:
        raise ValueError(
            "Selector paths must be `family`, `family/problem`, or `family/problem/difficulty`; "
            f"got {path!r}"
        )
    return parts


def _artifact_from_path(file_path: Path, instance_dir: Path) -> ArtifactFile:
    rel = normalize_relative_path(file_path.relative_to(instance_dir).as_posix())
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        return ArtifactFile(rel, json.loads(file_path.read_text(encoding="utf-8")), "json")
    if suffix in TEXT_SUFFIXES:
        return ArtifactFile(rel, file_path.read_text(encoding="utf-8"), "text")
    return ArtifactFile(rel, file_path.read_bytes(), "binary")
