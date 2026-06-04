# SPDX-License-Identifier: SSPL-1.0
# Copyright (C) 2026 ProtocolWarden
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from hashlib import sha256
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "scripts" / "custodian" / "run_with_boundary.sh"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def _boundary_artifact(path: Path, *, forbidden_names: list[str]) -> Path:
    payload = {
        "schema_kind": "boundary_artifact",
        "schema_version": "1.0.0",
        "artifact_kind": "boundary_disclosure_artifact",
        "source_graph_id": "private-manifest",
        "source_ref_or_commit": "abc123",
        "generated_at": "2026-05-12T00:00:00Z",
        "forbidden_names": forbidden_names,
        "allowed_aliases": ["ManagedProjectPublic"],
        "redacted_entities": ["private_impl"],
        "redaction_rules_applied": ["forbid_non_public_canonical_names"],
    }
    payload["artifact_hash"] = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fake_private_manifest(root: Path, *, call_file: Path | None = None) -> Path:
    module = _write(
        root / "src" / "private_manifest" / "export_boundary_artifact.py",
        """\
        from __future__ import annotations

        import argparse
        import json
        import os
        from hashlib import sha256
        from pathlib import Path


        def main() -> int:
            parser = argparse.ArgumentParser()
            parser.add_argument("--graph-root", required=True)
            parser.add_argument("--out", required=True)
            parser.add_argument("--profile")
            args = parser.parse_args()
            call_file = os.environ.get("PM_CALL_FILE")
            if call_file:
                Path(call_file).write_text(
                    json.dumps(
                        {
                            "graph_root": args.graph_root,
                            "out": args.out,
                            "profile": args.profile,
                        }
                    ),
                    encoding="utf-8",
                )
            payload = {
                "schema_kind": "boundary_artifact",
                "schema_version": "1.0.0",
                "artifact_kind": "boundary_disclosure_artifact",
                "source_graph_id": "private-manifest",
                "source_ref_or_commit": "abc123",
                "generated_at": "2026-05-12T00:00:00Z",
                "forbidden_names": ["PrivateImpl"],
                "allowed_aliases": ["ManagedProjectPublic"],
                "redacted_entities": ["private_impl"],
                "redaction_rules_applied": ["forbid_non_public_canonical_names"],
            }
            payload["artifact_hash"] = sha256(
                json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload), encoding="utf-8")
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """,
    )
    _write(root / "src" / "private_manifest" / "__init__.py", "")
    return module


def _fake_repo_root(root: Path) -> Path:
    (root / "src").mkdir(parents=True, exist_ok=True)
    return root


def _fake_custodian(cmd_path: Path, exit_code: int = 0) -> Path:
    script = _write(
        cmd_path,
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        out_file="${{1:-}}"
        if [[ -n "$out_file" ]]; then
          printf '%s' "${{REPOGRAPH_BOUNDARY_ARTIFACT_FILE:-}}" > "$out_file"
        fi
        exit {exit_code}
        """,
    )
    script.chmod(0o755)
    return script


def _run_wrapper(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(WRAPPER), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env=env,
    )


def test_existing_artifact_succeeds_without_invoking_export(tmp_path: Path) -> None:
    repo_root = _fake_repo_root(tmp_path / "repo")
    private_manifest_root = tmp_path / "private-manifest"
    call_file = tmp_path / "pm-call.json"
    _fake_private_manifest(private_manifest_root)
    repograph_root = _fake_repo_root(tmp_path / "RepoGraph")
    artifact = _boundary_artifact(tmp_path / "boundary.json", forbidden_names=["PrivateImpl"])
    capture = tmp_path / "custodian-env.txt"
    custodian = _fake_custodian(tmp_path / "custodian.sh")
    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    env["PM_CALL_FILE"] = str(call_file)
    result = _run_wrapper(
        "--repo-root",
        str(repo_root),
        "--private-manifest-root",
        str(private_manifest_root),
        "--repograph-root",
        str(repograph_root),
        "--boundary-artifact",
        str(artifact),
        "--custodian-command",
        f"{custodian} {capture}",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert capture.read_text(encoding="utf-8") == str(artifact)
    assert not call_file.exists()


def test_missing_artifact_fails_before_custodian(tmp_path: Path) -> None:
    repo_root = _fake_repo_root(tmp_path / "repo")
    private_manifest_root = tmp_path / "private-manifest"
    call_file = tmp_path / "pm-call.json"
    _fake_private_manifest(private_manifest_root)
    repograph_root = _fake_repo_root(tmp_path / "RepoGraph")
    missing = tmp_path / "missing.json"
    capture = tmp_path / "custodian-env.txt"
    custodian = _fake_custodian(tmp_path / "custodian.sh")
    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    env["PM_CALL_FILE"] = str(call_file)
    result = _run_wrapper(
        "--repo-root",
        str(repo_root),
        "--private-manifest-root",
        str(private_manifest_root),
        "--repograph-root",
        str(repograph_root),
        "--boundary-artifact",
        str(missing),
        "--custodian-command",
        f"{custodian} {capture}",
        env=env,
    )
    assert result.returncode != 0
    assert "Boundary artifact missing or empty" in result.stderr
    assert not capture.exists()
    assert not call_file.exists()


def test_generated_artifact_succeeds_and_exposes_env(tmp_path: Path) -> None:
    repo_root = _fake_repo_root(tmp_path / "repo")
    private_manifest_root = tmp_path / "private-manifest"
    call_file = tmp_path / "pm-call.json"
    _fake_private_manifest(private_manifest_root)
    repograph_root = _fake_repo_root(tmp_path / "RepoGraph")
    capture = tmp_path / "custodian-env.txt"
    custodian = _fake_custodian(tmp_path / "custodian.sh")
    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    env["PM_CALL_FILE"] = str(call_file)
    result = _run_wrapper(
        "--repo-root",
        str(repo_root),
        "--private-manifest-root",
        str(private_manifest_root),
        "--repograph-root",
        str(repograph_root),
        "--profile",
        "PUBLIC_SAFE",
        "--custodian-command",
        f"{custodian} {capture}",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    artifact_path = Path(capture.read_text(encoding="utf-8"))
    assert not artifact_path.exists()
    assert json.loads(call_file.read_text(encoding="utf-8"))["out"] == str(artifact_path)


def test_custodian_exit_code_is_preserved(tmp_path: Path) -> None:
    repo_root = _fake_repo_root(tmp_path / "repo")
    artifact = _boundary_artifact(tmp_path / "boundary.json", forbidden_names=["PrivateImpl"])
    capture = tmp_path / "custodian-env.txt"
    custodian = _fake_custodian(tmp_path / "custodian.sh", exit_code=17)
    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    result = _run_wrapper(
        "--repo-root",
        str(repo_root),
        "--boundary-artifact",
        str(artifact),
        "--custodian-command",
        f"{custodian} {capture}",
        env=env,
    )
    assert result.returncode == 17
    assert capture.read_text(encoding="utf-8") == str(artifact)


def test_keep_artifacts_preserves_generated_output(tmp_path: Path) -> None:
    repo_root = _fake_repo_root(tmp_path / "repo")
    private_manifest_root = tmp_path / "private-manifest"
    call_file = tmp_path / "pm-call.json"
    _fake_private_manifest(private_manifest_root, call_file=call_file)
    repograph_root = _fake_repo_root(tmp_path / "RepoGraph")
    capture = tmp_path / "custodian-env.txt"
    custodian = _fake_custodian(tmp_path / "custodian.sh")
    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    result = _run_wrapper(
        "--repo-root",
        str(repo_root),
        "--private-manifest-root",
        str(private_manifest_root),
        "--repograph-root",
        str(repograph_root),
        "--keep-artifacts",
        "--custodian-command",
        f"{custodian} {capture}",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    artifact_path = Path(capture.read_text(encoding="utf-8"))
    assert artifact_path.exists()
    assert artifact_path.parent.exists()
    shutil.rmtree(artifact_path.parent)


def test_debug_does_not_print_forbidden_names(tmp_path: Path) -> None:
    repo_root = _fake_repo_root(tmp_path / "repo")
    artifact = _boundary_artifact(
        tmp_path / "boundary.json",
        forbidden_names=["VerySecretRepo", "AnotherSecretRepo"],
    )
    capture = tmp_path / "custodian-env.txt"
    custodian = _fake_custodian(tmp_path / "custodian.sh")
    env = os.environ.copy()
    env["PYTHON_BIN"] = sys.executable
    result = _run_wrapper(
        "--repo-root",
        str(repo_root),
        "--boundary-artifact",
        str(artifact),
        "--debug",
        "--custodian-command",
        f"{custodian} {capture}",
        env=env,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, result.stderr
    assert "VerySecretRepo" not in combined
    assert "AnotherSecretRepo" not in combined
