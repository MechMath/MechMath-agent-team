#!/usr/bin/env python3
"""
CLI for running Claude on Lean theorem proving tasks.

Usage:
    python -m scripts.run_claude run <target> [options]
    python -m scripts.run_claude batch <config_file> [options]
    python -m scripts.run_claude from-folder <folder> [options]
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, List

import fire
import yaml

from .task import TaskMetadata, TaskResult
from .runner import run_task, run_tasks
from .lean_checker import find_lean_files


class ClaudeRunner:
    """Claude runner CLI for Lean theorem proving tasks."""

    @staticmethod
    def _print_kill_hint():
        """Print emergency-stop hint for this runner process."""
        pid = os.getpid()
        print(f"[info] Runner current pid={pid}, one-click stop command: kill -TERM {pid}")

    def run(
        self,
        target: str,
        task_type: str = "auto",
        prompt: Optional[str] = None,
        prompt_file: Optional[str] = None,
        cwd: Optional[str] = None,
        max_rounds: int = 20,
        check: bool = True,
        sleep: float = 1.0,
        result_dir: Optional[str] = None,
        mcp_log_name: Optional[str] = None,
        permission_mode: str = "bypassPermissions",
        json_output: bool = False,
    ) -> int:
        """
        Run a single task.

        Args:
            target: Target path (file or folder)
            task_type: Task type (file / folder / auto)
            prompt: Prompt content
            prompt_file: Prompt file path
            cwd: Claude working directory
            max_rounds: Maximum rounds
            check: Whether to check after completion
            sleep: Sleep between rounds (seconds)
            result_dir: Result directory (JSON files)
            mcp_log_name: MCP log name (sets $MCP_LOG_NAME)
            permission_mode: Permission mode
            json_output: Whether to use JSON output format

        Returns:
            Exit code (0 for success, 1 for failure)

        Examples:
            # Single file
            python -m scripts.run_claude run /path/to/file.lean --prompt-file prompt.txt

            # Folder
            python -m scripts.run_claude run /path/to/folder --task-type folder --prompt "..."
        """
        self._print_kill_hint()
        target_path = Path(target).resolve()

        # Auto-detect task_type
        if task_type == "auto":
            task_type = "file" if target_path.is_file() else "folder"

        # Validate task_type
        if task_type not in ("file", "folder"):
            print(f"[error] Invalid task_type: {task_type}", file=sys.stderr)
            return 1

        # Validate prompt
        if not prompt and not prompt_file:
            print("[error] Either --prompt or --prompt-file must be provided", file=sys.stderr)
            return 1

        # Build TaskMetadata
        task = TaskMetadata(
            task_type=task_type,
            target_path=target_path,
            prompt=prompt,
            prompt_file=prompt_file,
            cwd=cwd,
            max_rounds=max_rounds,
            check_after_complete=check,
            sleep_between_rounds=sleep,
            result_dir=result_dir,
            mcp_log_name=mcp_log_name,
            permission_mode=permission_mode,
            output_format="json" if json_output else None,
        )

        # Run task
        result = run_task(task)

        # Print summary
        self._print_result(result)

        return 0 if result.success else 1

    def batch(
        self,
        config_file: str,
        parallel: bool = False,
        max_workers: int = 1,
    ) -> int:
        """
        Run batch tasks from config file (JSON or YAML).

        Args:
            config_file: Config file path (JSON or YAML)
            parallel: Whether to run in parallel
            max_workers: Maximum parallel workers

        Returns:
            Exit code (0 if all succeed, 1 if any fails)

        Config file format (YAML example):
            defaults:
              prompt_file: /path/to/prompt.txt
              max_rounds: 20
              cwd: /path/to/project

            tasks:
              - task_type: file
                target_path: /path/to/file.lean
                mcp_log_name: file1
              - task_type: folder
                target_path: /path/to/folder

        Examples:
            python -m scripts.run_claude batch tasks.yaml
            python -m scripts.run_claude batch tasks.yaml --parallel --max-workers 4
        """
        self._print_kill_hint()
        config_path = Path(config_file).resolve()
        if not config_path.exists():
            print(f"[error] Config file not found: {config_path}", file=sys.stderr)
            return 1

        with open(config_path, "r", encoding="utf-8") as f:
            # Support both JSON and YAML
            if config_path.suffix in (".yaml", ".yml"):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)

        defaults = config.get("defaults", {})
        task_dicts = config.get("tasks", [])

        if not task_dicts:
            print("[warn] No tasks in config file")
            return 0

        # Build TaskMetadata list
        tasks = []
        for task_dict in task_dicts:
            # Merge defaults
            merged = {**defaults, **task_dict}
            task = TaskMetadata.from_dict(merged)
            tasks.append(task)

        print(f"[info] Loaded {len(tasks)} tasks from config")

        # Run tasks
        results = run_tasks(tasks, parallel=parallel, max_workers=max_workers)

        # Print summary
        self._print_batch_summary(results)

        # Return 1 if any failed
        return 0 if all(r.success for r in results) else 1

    def from_folder(
        self,
        folder: str,
        prompt: Optional[str] = None,
        prompt_file: Optional[str] = None,
        cwd: Optional[str] = None,
        max_rounds: int = 20,
        check: bool = True,
        sleep: float = 1.0,
        result_dir: Optional[str] = None,
        permission_mode: str = "bypassPermissions",
        parallel: bool = False,
        max_workers: int = 1,
    ) -> int:
        """
        Generate and run tasks from a folder (one task per .lean file).

        Args:
            folder: Folder containing .lean files
            prompt: Prompt content
            prompt_file: Prompt file path
            cwd: Claude working directory
            max_rounds: Maximum rounds
            check: Whether to check after completion
            sleep: Sleep between rounds
            result_dir: Result directory (JSON files)
            permission_mode: Permission mode
            parallel: Whether to run in parallel
            max_workers: Maximum parallel workers

        Returns:
            Exit code (0 if all succeed, 1 if any fails)

        Examples:
            python -m scripts.run_claude from-folder /path/to/folder --prompt-file prompt.txt
            python -m scripts.run_claude from-folder /path/to/folder --prompt-file prompt.txt --parallel --max-workers 4
        """
        self._print_kill_hint()
        folder_path = Path(folder).resolve()
        if not folder_path.exists():
            print(f"[error] Folder not found: {folder_path}", file=sys.stderr)
            return 1

        # Validate prompt
        if not prompt and not prompt_file:
            print("[error] Either --prompt or --prompt-file must be provided", file=sys.stderr)
            return 1

        # Find all .lean files
        lean_files = find_lean_files(folder_path)
        if not lean_files:
            print(f"[warn] No .lean files found in {folder_path}")
            return 0

        print(f"[info] Found {len(lean_files)} .lean files")

        # Build tasks
        tasks = []
        for lean_file in lean_files:
            task = TaskMetadata(
                task_type="file",
                target_path=lean_file,
                prompt=prompt,
                prompt_file=prompt_file,
                cwd=cwd,
                max_rounds=max_rounds,
                check_after_complete=check,
                sleep_between_rounds=sleep,
                result_dir=result_dir,
                mcp_log_name=lean_file.stem,
                permission_mode=permission_mode,
            )
            tasks.append(task)

        # Run tasks
        results = run_tasks(tasks, parallel=parallel, max_workers=max_workers)

        # Print summary
        self._print_batch_summary(results)

        return 0 if all(r.success for r in results) else 1

    def _print_result(self, result: TaskResult):
        """Print single task result."""
        status = "SUCCESS" if result.success else "FAILED"
        print(f"\n{'=' * 60}")
        print(f"Task: {result.task_id}")
        print(f"Status: {status}")
        print(f"End Reason: {result.end_reason}")
        print(f"Rounds: {result.rounds_used}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        if result.error_message:
            print(f"Error: {result.error_message}")

        # Print line count changes
        self._print_line_changes(result)

        print("=" * 60)

    def _print_line_changes(self, result: TaskResult):
        """Print line count changes between first and last round."""
        if len(result.round_results) < 1:
            return

        first = result.round_results[0].line_counts
        last = result.round_results[-1].line_counts

        if not first or not last:
            return

        changes = []
        for filename in first:
            if filename in last:
                diff = last[filename] - first[filename]
                if diff != 0:
                    ratio = diff / first[filename] * 100 if first[filename] > 0 else 0
                    changes.append((filename, first[filename], last[filename], diff, ratio))

        if changes:
            print("\nLine changes:")
            for filename, initial, final, diff, ratio in changes:
                sign = "+" if diff > 0 else ""
                print(f"  {filename}: {initial} -> {final} ({sign}{diff}, {ratio:+.1f}%)")

    def _print_batch_summary(self, results: List[TaskResult]):
        """Print batch results summary."""
        total = len(results)
        succeeded = sum(1 for r in results if r.success)
        failed = total - succeeded
        total_duration = sum(r.duration_seconds for r in results)

        print(f"\n{'=' * 60}")
        print("BATCH SUMMARY")
        print("=" * 60)
        print(f"Total tasks: {total}")
        print(f"Succeeded: {succeeded}")
        print(f"Failed: {failed}")
        print(f"Total duration: {total_duration:.1f}s")

        if failed > 0:
            print("\nFailed tasks:")
            for r in results:
                if not r.success:
                    print(f"  - {r.task_id}: {r.end_reason}")
                    if r.error_message:
                        print(f"    Error: {r.error_message}")

        # Collect all line changes
        all_changes = []
        for r in results:
            if len(r.round_results) >= 1:
                first = r.round_results[0].line_counts
                last = r.round_results[-1].line_counts
                for filename in first:
                    if filename in last:
                        diff = last[filename] - first[filename]
                        if diff != 0:
                            ratio = diff / first[filename] * 100 if first[filename] > 0 else 0
                            all_changes.append((filename, first[filename], last[filename], diff, ratio))

        if all_changes:
            print("\nLine changes (all tasks):")
            total_initial = sum(c[1] for c in all_changes)
            total_final = sum(c[2] for c in all_changes)
            total_diff = total_final - total_initial

            for filename, initial, final, diff, ratio in all_changes:
                sign = "+" if diff > 0 else ""
                print(f"  {filename}: {initial} -> {final} ({sign}{diff}, {ratio:+.1f}%)")

            if total_initial > 0:
                total_ratio = total_diff / total_initial * 100
                sign = "+" if total_diff > 0 else ""
                print(f"  ----")
                print(f"  Total: {total_initial} -> {total_final} ({sign}{total_diff}, {total_ratio:+.1f}%)")

        print("=" * 60)


def main():
    """CLI entry point."""
    fire.Fire(ClaudeRunner)


if __name__ == "__main__":
    main()
