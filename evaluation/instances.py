from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class ArtifactFile:
    relative_path: str
    content: Any
    kind: str

    @property
    def name(self) -> str:
        return PurePosixPath(self.relative_path).name

    @property
    def suffix(self) -> str:
        return PurePosixPath(self.relative_path).suffix.lower()


@dataclass(frozen=True)
class BenchmarkInstance:
    family: str
    problem: str
    difficulty: str
    instance_id: str
    files: tuple[ArtifactFile, ...]
    origin: str = "mmopt_release"
    source_dir: str | None = None

    @property
    def instance_key(self) -> str:
        return f"{self.family}/{self.problem}/{self.difficulty}/{self.instance_id}"

    @property
    def key(self) -> str:
        return self.instance_key

    @property
    def identifier(self) -> str:
        return self.instance_id

    def file(self, relative_path: str) -> ArtifactFile:
        normalized = normalize_relative_path(relative_path)
        for artifact in self.files:
            if artifact.relative_path == normalized:
                return artifact
        raise KeyError(f"Artifact not found for {self.instance_key}: {relative_path}")

    def has_file(self, relative_path: str) -> bool:
        try:
            self.file(relative_path)
        except KeyError:
            return False
        return True

    def text(self, relative_path: str) -> str:
        artifact = self.file(relative_path)
        if artifact.kind == "text":
            return str(artifact.content)
        if artifact.kind == "json":
            return json.dumps(artifact.content, ensure_ascii=False, indent=2)
        raise TypeError(f"Artifact is not text: {relative_path} ({artifact.kind})")

    def json(self, relative_path: str) -> Any:
        artifact = self.file(relative_path)
        if artifact.kind == "json":
            return artifact.content
        if artifact.kind == "text":
            return json.loads(str(artifact.content))
        raise TypeError(f"Artifact is not JSON: {relative_path} ({artifact.kind})")

    def bytes(self, relative_path: str) -> bytes:
        artifact = self.file(relative_path)
        if artifact.kind != "binary":
            raise TypeError(f"Artifact is not binary: {relative_path} ({artifact.kind})")
        content = artifact.content
        if not isinstance(content, bytes):
            raise TypeError(f"Binary artifact content is not bytes: {relative_path}")
        return content

    def visuals(self) -> tuple[ArtifactFile, ...]:
        return tuple(
            sorted(
                (
                    artifact
                    for artifact in self.files
                    if artifact.relative_path.startswith("visuals/")
                    and artifact.suffix in IMAGE_EXTS
                    and artifact.kind == "binary"
                ),
                key=lambda artifact: artifact.relative_path,
            )
        )

    def metadata(self) -> dict[str, str]:
        return {
            "instance_key": self.instance_key,
            "instance_origin": self.origin,
            "family": self.family,
            "problem": self.problem,
            "difficulty": self.difficulty,
            "instance_id": self.instance_id,
        }

    def export_to(self, root: str | Path) -> Path:
        instance_dir = Path(root).expanduser() / self.family / self.problem / self.difficulty / self.instance_id
        instance_dir.mkdir(parents=True, exist_ok=True)
        for artifact in self.files:
            rel = normalize_relative_path(artifact.relative_path)
            target = instance_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if artifact.kind == "json":
                target.write_text(json.dumps(artifact.content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            elif artifact.kind == "text":
                target.write_text(str(artifact.content), encoding="utf-8")
            elif artifact.kind == "binary":
                if not isinstance(artifact.content, bytes):
                    raise TypeError(f"Binary artifact content is not bytes: {artifact.relative_path}")
                target.write_bytes(artifact.content)
            else:
                raise ValueError(f"Unsupported artifact kind: {artifact.kind}")
        return instance_dir


def normalize_relative_path(path: str) -> str:
    pure = PurePosixPath(str(path).replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"Artifact paths must be relative and stay inside the instance: {path}")
    normalized = pure.as_posix()
    if normalized in {"", "."}:
        raise ValueError("Artifact path must not be empty.")
    return normalized


def instance_from_released_artifacts(released: Any) -> BenchmarkInstance:
    files = tuple(
        ArtifactFile(
            relative_path=normalize_relative_path(artifact.relative_path),
            content=artifact.content,
            kind=artifact.kind,
        )
        for artifact in released.files
    )
    return BenchmarkInstance(
        family=released.family,
        problem=released.problem,
        difficulty=released.difficulty,
        instance_id=released.instance_id,
        files=files,
        origin="mmopt_release",
    )


def ensure_instances(instances: Iterable[BenchmarkInstance]) -> tuple[BenchmarkInstance, ...]:
    return tuple(instances)
