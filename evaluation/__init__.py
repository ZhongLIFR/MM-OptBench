from __future__ import annotations

from typing import Any, Iterable

from .benchmarks import ArtifactBenchmark, Benchmark, parse_instance_key
from .instances import ArtifactFile, BenchmarkInstance
from .prompts import build_instance_messages, build_instance_text
from .runner import evaluate as _evaluate_runs
from .runner import run_instance as _run_instance
from .workflows import (
    EVAL_MODE_MULTIMODAL,
    EVAL_MODE_ORACLE_READING,
    EVAL_MODE_TWO_STAGE,
    EVAL_MODE_VERIFIED_EXTRACTION,
    diagnose_extraction_target,
    diagnose_instance_target,
    grade_instance_response,
    resume_eval_dir,
    run_experiment as _run_experiment,
)


def evaluate(
    instances: Iterable[BenchmarkInstance],
    *,
    models: list[str],
    **kwargs: Any,
):
    """Evaluate one or more benchmark instances."""
    return _evaluate_runs(instances, models=models, **kwargs)


def evaluate_instance(
    instance: BenchmarkInstance,
    *,
    model: str,
    **kwargs: Any,
):
    """Evaluate a single benchmark instance."""
    return _run_instance(instance, model=model, **kwargs)


def run_experiment(
    instances: Iterable[BenchmarkInstance],
    *,
    models: list[str],
    mode: str = EVAL_MODE_MULTIMODAL,
    **kwargs: Any,
):
    """Run a named benchmark experiment mode over selected instances."""
    return _run_experiment(instances, models=models, mode=mode, **kwargs)


__all__ = [
    "ArtifactBenchmark",
    "ArtifactFile",
    "Benchmark",
    "BenchmarkInstance",
    "EVAL_MODE_MULTIMODAL",
    "EVAL_MODE_ORACLE_READING",
    "EVAL_MODE_TWO_STAGE",
    "EVAL_MODE_VERIFIED_EXTRACTION",
    "build_instance_messages",
    "build_instance_text",
    "diagnose_extraction_target",
    "diagnose_instance_target",
    "evaluate",
    "evaluate_instance",
    "grade_instance_response",
    "parse_instance_key",
    "resume_eval_dir",
    "run_experiment",
]
