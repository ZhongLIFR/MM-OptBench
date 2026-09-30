from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .runner import DEFAULT_BASE_URL, DEFAULT_API_KEY_ENV, run_instance
from .benchmarks import ArtifactBenchmark, Benchmark
from .workflows import (
    EVAL_MODE_MULTIMODAL,
    EVAL_MODE_ORACLE_READING,
    EVAL_MODE_TWO_STAGE,
    EVAL_MODE_VERIFIED_EXTRACTION,
    diagnose_extraction_target,
    diagnose_instance_target,
    grade_instance_response,
    resume_eval_dir,
    run_experiment,
)


def main(argv: list[str] | None = None, *, prog: str = "mmopt-eval") -> None:
    parser = _parser(prog=prog)
    args = parser.parse_args(argv)
    if args.command == "problems":
        records = Benchmark().problems(
            family=args.family,
            problem=args.problem,
            difficulty=args.difficulty,
            paths=_split_paths(args.paths),
        )
        _print_json(records)
    elif args.command == "list":
        instances = Benchmark().instances(
            family=args.family,
            problem=args.problem,
            difficulty=args.difficulty,
            paths=_split_paths(args.paths),
            max_instances=args.limit,
        )
        _print_json([instance.metadata() for instance in instances])
    elif args.command == "run-instance":
        instance = _load_single_instance(args)
        run_dir, _ = run_instance(
            instance,
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            api_key_env=args.api_key_env,
            include_canonical=False,
            response_contract=args.response_contract,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            verify_ssl=not args.insecure,
            output_root=args.output_dir,
            dry_run=args.dry_run,
            python_cmd=args.python_cmd,
            timeout_seconds=args.timeout_seconds,
            tolerance=args.tolerance,
        )
        print(run_dir)
    elif args.command == "experiment":
        instances = _load_eval_family_instances(args)
        eval_dir = run_experiment(
            instances,
            models=args.models,
            mode=args.mode,
            base_url=args.base_url,
            api_key=args.api_key,
            api_key_env=args.api_key_env,
            include_canonical=False,
            response_contract=args.response_contract,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            stage1_max_tokens=getattr(args, "stage1_max_tokens", args.max_tokens),
            stage2_max_tokens=getattr(args, "stage2_max_tokens", args.max_tokens),
            extraction_max_tokens=getattr(args, "extraction_max_tokens", args.max_tokens),
            downstream_max_tokens=getattr(args, "downstream_max_tokens", args.max_tokens),
            verify_ssl=not args.insecure,
            output_dir=args.eval_output_dir,
            run_output_dir=args.run_output_dir,
            dry_run=args.dry_run,
            python_cmd=args.python_cmd,
            timeout_seconds=args.timeout_seconds,
            tolerance=args.tolerance,
        )
        print(eval_dir)
    elif args.command == "resume-experiment":
        eval_dir = resume_eval_dir(
            args.eval_dir,
            run_output_dir=args.run_output_dir,
            base_url=args.base_url,
            api_key=args.api_key,
            api_key_env=args.api_key_env,
            verify_ssl=None if args.insecure is None else not args.insecure,
            dry_run=args.dry_run,
            python_cmd=args.python_cmd,
            timeout_seconds=args.timeout_seconds,
            tolerance=args.tolerance,
        )
        print(eval_dir)
    elif args.command == "grade":
        instance = _load_single_instance(args)
        _print_json(grade_instance_response(instance, args.response, tolerance=args.tolerance))
    elif args.command == "diagnose":
        instance = _load_single_instance(args)
        _print_json(
            diagnose_instance_target(
                instance,
                args.target,
                python_cmd=args.python_cmd,
                timeout_seconds=args.timeout_seconds,
                tolerance=args.tolerance,
            )
        )
    elif args.command == "diagnose-extraction":
        instance = _load_single_instance(args)
        _print_json(diagnose_extraction_target(instance, args.target, tolerance=args.tolerance))
    else:
        raise SystemExit(f"Unsupported command: {args.command}")


def _parser(*, prog: str = "mmopt-eval") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    sub = parser.add_subparsers(dest="command", required=True)

    problems_cmd = sub.add_parser("problems", help="List included released problems and their instance keys.")
    _add_release_selectors(problems_cmd, include_limit=False)

    list_cmd = sub.add_parser("list", help="List released dataset instances.")
    _add_release_selectors(list_cmd)

    run_instance_cmd = sub.add_parser("run-instance", help="Evaluate one released instance or one local instance.")
    run_instance_cmd.add_argument("--instance", help="Released instance key: family/problem/difficulty/instance_id.")
    run_instance_cmd.add_argument("--instance-dir", help="Path to one local instance directory.")
    run_instance_cmd.add_argument("--model", required=True)
    _add_eval_options(run_instance_cmd)
    run_instance_cmd.add_argument("--output-dir", default="output/mmopt_runs")

    experiment = sub.add_parser("experiment", help="Run a benchmark experiment over selected instances.")
    _add_family_eval_args(experiment, default_response_contract="minimal_sections")
    experiment.add_argument(
        "--mode",
        choices=[
            EVAL_MODE_MULTIMODAL,
            EVAL_MODE_ORACLE_READING,
            EVAL_MODE_VERIFIED_EXTRACTION,
            EVAL_MODE_TWO_STAGE,
        ],
        default=EVAL_MODE_MULTIMODAL,
    )
    experiment.add_argument("--stage1-max-tokens", type=int, default=32768)
    experiment.add_argument("--stage2-max-tokens", type=int, default=32768)
    experiment.add_argument("--extraction-max-tokens", type=int, default=32768)
    experiment.add_argument("--downstream-max-tokens", type=int, default=32768)

    resume = sub.add_parser("resume-experiment", help="Resume an interrupted experiment directory.")
    _add_resume_args(resume)

    grade = sub.add_parser("grade", help="Compare a saved response against benchmark ground truth.")
    grade.add_argument("response")
    grade.add_argument("--instance", help="Released instance key: family/problem/difficulty/instance_id.")
    grade.add_argument("--instance-dir", help="Path to one local instance directory.")
    grade.add_argument("--tolerance", type=float, default=1e-6)

    diagnose = sub.add_parser("diagnose", help="Diagnose a run directory or response artifact.")
    diagnose.add_argument("target")
    diagnose.add_argument("--instance", help="Released instance key: family/problem/difficulty/instance_id.")
    diagnose.add_argument("--instance-dir", help="Path to one local instance directory.")
    diagnose.add_argument("--python-cmd", default=sys.executable)
    diagnose.add_argument("--timeout-seconds", type=int, default=1800)
    diagnose.add_argument("--tolerance", type=float, default=1e-6)

    diagnose_extraction = sub.add_parser("diagnose-extraction", help="Diagnose extraction-only output.")
    diagnose_extraction.add_argument("target")
    diagnose_extraction.add_argument("--instance", help="Released instance key: family/problem/difficulty/instance_id.")
    diagnose_extraction.add_argument("--instance-dir", help="Path to one local instance directory.")
    diagnose_extraction.add_argument("--tolerance", type=float, default=1e-6)

    return parser


def _add_release_selectors(parser: argparse.ArgumentParser, *, include_limit: bool = True) -> None:
    parser.add_argument("--family")
    parser.add_argument("--problem")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"])
    parser.add_argument("--paths")
    if include_limit:
        parser.add_argument("--limit", type=int, dest="limit")


def _add_eval_options(parser: argparse.ArgumentParser, *, default_response_contract: str = "minimal_sections") -> None:
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key")
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument(
        "--response-contract",
        choices=["minimal_sections", "fullsolve_json", "extraction_json"],
        default=default_response_contract,
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=32768)
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--python-cmd", default=sys.executable)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--tolerance", type=float, default=1e-6)


def _add_family_eval_args(parser: argparse.ArgumentParser, *, default_response_contract: str) -> None:
    _add_release_selectors(parser)
    parser.add_argument("--family-dir", help="Path to one local family directory.")
    parser.add_argument("--models", nargs="+", required=True)
    _add_eval_options(parser, default_response_contract=default_response_contract)
    parser.add_argument("--eval-output-dir", default="output/mmopt_eval")
    parser.add_argument("--run-output-dir", default="output/mmopt_runs")


def _add_resume_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("eval_dir")
    parser.add_argument("--base-url")
    parser.add_argument("--api-key")
    parser.add_argument("--api-key-env")
    parser.add_argument("--run-output-dir", default=None)
    parser.add_argument("--insecure", action="store_true", default=None)
    parser.add_argument("--dry-run", action="store_true", default=None)
    parser.add_argument("--python-cmd")
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--tolerance", type=float)


def _load_single_instance(args: argparse.Namespace):
    if args.instance_dir:
        return ArtifactBenchmark().instances(instance_dir=args.instance_dir)[0]
    if not args.instance:
        raise SystemExit("run-instance requires --instance or --instance-dir.")
    return Benchmark().instance(args.instance)


def _load_eval_family_instances(args: argparse.Namespace):
    family_dir = getattr(args, "family_dir", None)
    if family_dir:
        return ArtifactBenchmark().instances(
            family_dir=family_dir,
            difficulty=args.difficulty,
            problem=args.problem,
            max_instances=args.limit,
        )
    return Benchmark().instances(
        family=args.family,
        problem=args.problem,
        difficulty=args.difficulty,
        paths=_split_paths(args.paths),
        max_instances=args.limit,
    )


def _split_paths(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
