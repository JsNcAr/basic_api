"""
scripts/release.py: version bumps, pyproject and changelog handling, and a full
`prepare` run in a throwaway repository. No database and nothing from basic_api.
"""

import datetime as dt
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "release.py"

_spec = importlib.util.spec_from_file_location("release_script", SCRIPT)
assert _spec is not None and _spec.loader is not None
release = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = release  # dataclasses look their module up here
_spec.loader.exec_module(release)

PYPROJECT = """[project]
name = "demo-api"
version = "0.1.0"
dependencies = [
    "fastapi (>=0.142,<1.0)",
]

[tool.poetry]
packages = [{include = "demo_api", from = "src"}]

[tool.other]
version = "9.9.9"
"""
STARTER_TABLE = "\n[tool.release]\nstarter = true\n"

CHANGELOG = """# Changelog

Format: Keep a Changelog.

## [Unreleased]

### Added
- A thing (#3).

## [0.1.0] - 2026-01-01

### Added
- The first thing.
"""


# -- versions -----------------------------------------------------------------


@pytest.mark.parametrize(
    "current, part, expected",
    [
        ("0.1.0", "patch", "0.1.1"),
        ("0.1.3", "minor", "0.2.0"),
        ("0.4.3", "major", "1.0.0"),
        ("1.0.0-rc.2", "patch", "1.0.0"),
        ("1.0.0-rc.2", "minor", "1.0.0"),
        ("0.9.0", "1.0.0-rc.1", "1.0.0-rc.1"),
        ("1.0.0-rc.1", "1.0.0", "1.0.0"),
    ],
)
def test_bump(current, part, expected):
    assert release.bump(current, part) == expected


@pytest.mark.parametrize("current, part", [("1.0.0", "1.0.0-rc.1"), ("0.2.0", "0.2.0")])
def test_an_explicit_version_must_be_newer(current, part):
    with pytest.raises(release.ReleaseError):
        release.bump(current, part)


@pytest.mark.parametrize("bad", ["v0.3", "1.2", "1.2.3+build", "latest"])
def test_malformed_versions_are_refused(bad):
    with pytest.raises(release.ReleaseError):
        release.bump("0.2.0", bad)


def test_prerelease_detection():
    assert release.is_prerelease("1.0.0-rc.1")
    assert not release.is_prerelease("1.0.0")


# -- pyproject ----------------------------------------------------------------


def test_read_project_takes_name_version_and_marker():
    project = release.read_project(PYPROJECT)
    assert (project.name, project.version, project.starter) == (
        "demo-api",
        "0.1.0",
        False,
    )
    assert release.read_project(PYPROJECT + STARTER_TABLE).starter is True
    assert (
        release.read_project(PYPROJECT + "\n[tool.release]\nstarter = false\n").starter
        is False
    )


def test_read_project_needs_a_project_table():
    with pytest.raises(release.ReleaseError):
        release.read_project('[tool.poetry]\nname = "x"\nversion = "1.0.0"\n')
    with pytest.raises(release.ReleaseError):
        release.read_project("not = [toml")


def test_write_version_touches_only_the_project_version():
    updated = release.write_version(PYPROJECT, "0.2.0")
    assert release.read_project(updated).version == "0.2.0"
    assert 'version = "9.9.9"' in updated  # the other table is untouched
    assert updated.replace('version = "0.2.0"', 'version = "0.1.0"', 1) == PYPROJECT


# -- remotes ------------------------------------------------------------------


@pytest.mark.parametrize(
    "remote, expected",
    [
        (
            "git@github.com:JsNcAr/basic_api.git",
            "https://github.com/JsNcAr/basic_api/actions",
        ),
        (
            "https://github.com/JsNcAr/basic_api",
            "https://github.com/JsNcAr/basic_api/actions",
        ),
        (
            "ssh://git@gitlab.example.net:2222/group/sub/repo.git",
            "https://gitlab.example.net/group/sub/repo/-/pipelines",
        ),
        (
            "git@gitlab.example.net:group/repo.git",
            "https://gitlab.example.net/group/repo/-/pipelines",
        ),
        (
            "https://gitlab.example.net/group/repo.git",
            "https://gitlab.example.net/group/repo/-/pipelines",
        ),
        ("", "<the repository's CI page>"),
    ],
)
def test_pipelines_url_handles_github_and_gitlab_remotes(remote, expected):
    assert release.pipelines_url(remote) == expected


# -- changelog ----------------------------------------------------------------


def _commit(subject, body=""):
    return release.Commit("0123456789abcdef", subject, body)


def test_generated_notes_group_conventional_commits_and_skip_housekeeping():
    rendered = release.render_section(
        [
            _commit("feat(users): add avatars"),
            _commit("fix: 500 on empty body"),
            _commit("perf: faster hashing"),
            _commit("refactor: split routers"),
            _commit("security: rotate the sentinel hash"),
            _commit("docs: explain tokens"),
            _commit("feat!: drop /v0"),
            _commit("fix: change ids", "BREAKING CHANGE: ids are UUIDs now"),
            _commit("chore(release): v0.1.0"),
            _commit("chore: bump deps"),
            _commit("test: more cases"),
            _commit("Merge pull request #12 from x/y"),
        ]
    )
    headings = [line for line in rendered.splitlines() if line.startswith("### ")]
    assert headings == [
        "### Breaking changes",
        "### Added",
        "### Changed",
        "### Performance",
        "### Fixed",
        "### Security",
        "### Documentation",
    ]
    assert "- **users:** add avatars (0123456)" in rendered
    assert "- drop /v0 (0123456)" in rendered
    assert "- change ids (0123456)" in rendered
    for skipped in ("v0.1.0", "bump deps", "more cases", "Merge pull"):
        assert skipped not in rendered
    assert release.render_section([_commit("chore: nothing")]) == ""


def test_split_unreleased():
    head, body, rest = release.split_unreleased(CHANGELOG)
    assert head.endswith("Keep a Changelog.\n\n")
    assert body == "### Added\n- A thing (#3)."
    assert rest.startswith("## [0.1.0] - 2026-01-01")
    with pytest.raises(release.ReleaseError):
        release.split_unreleased("# Changelog\n\n## [0.1.0]\n")


def test_add_release_moves_unreleased_under_the_version():
    updated, notes = release.add_release(
        CHANGELOG, "0.2.0", "### Fixed\n- generated", dt.date(2026, 10, 12)
    )
    assert notes == "### Added\n- A thing (#3)."  # written notes win
    expected = (
        "## [Unreleased]\n\n## [0.2.0] - 2026-10-12\n\n"
        "### Added\n- A thing (#3).\n\n## [0.1.0]"
    )
    assert expected in updated
    assert release.release_notes(updated, "0.2.0") == notes
    assert release.release_notes(updated, "0.1.0") == "### Added\n- The first thing."


def test_add_release_falls_back_to_generated_notes_and_refuses_nothing():
    empty = CHANGELOG.replace("### Added\n- A thing (#3).\n\n", "")
    updated, notes = release.add_release(
        empty, "0.2.0", "### Fixed\n- generated", dt.date(2026, 10, 12)
    )
    assert notes == "### Fixed\n- generated"
    assert "## [0.2.0] - 2026-10-12\n\n### Fixed\n- generated" in updated
    with pytest.raises(release.ReleaseError):
        release.add_release(empty, "0.2.0", "", dt.date(2026, 10, 12))


def test_release_notes_needs_the_section():
    with pytest.raises(release.ReleaseError):
        release.release_notes(CHANGELOG, "0.3.0")


# -- a full prepare run in a throwaway repository -----------------------------


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A clone with pyproject and changelog, pushed to a bare remote on `main`."""
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(remote), str(work))
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "Test")
    (work / "pyproject.toml").write_text(PYPROJECT)
    (work / "CHANGELOG.md").write_text(CHANGELOG)
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "feat: first")
    _git(work, "push", "-q", "-u", "origin", "main")
    monkeypatch.setattr(release, "ROOT", work)
    monkeypatch.setattr(release, "PYPROJECT", work / "pyproject.toml")
    monkeypatch.setattr(release, "CHANGELOG", work / "CHANGELOG.md")
    # Never touch this machine's Poetry environment from the test.
    monkeypatch.setattr(release, "refresh_installed_metadata", lambda: None)
    return work


def test_prepare_commits_tags_and_leaves_unreleased_empty(repo, capsys):
    assert release.main(["prepare", "minor", "--skip-tests", "--no-push", "--yes"]) == 0

    assert (
        release.read_project((repo / "pyproject.toml").read_text()).version == "0.2.0"
    )
    assert _git(repo, "log", "-1", "--format=%s") == "chore(release): v0.2.0"
    assert _git(repo, "status", "--porcelain") == ""
    tag_message = _git(repo, "tag", "-l", "--format=%(contents)", "v0.2.0")
    assert tag_message.startswith("v0.2.0\n\n### Added\n- A thing (#3).")
    _head, body, _rest = release.split_unreleased((repo / "CHANGELOG.md").read_text())
    assert body == ""
    assert "Not pushed" in capsys.readouterr().out
    assert _git(repo, "ls-remote", "--tags", "origin") == ""  # --no-push kept it local

    assert release.main(["check-version", "v0.2.0"]) == 0
    assert release.main(["check-version", "refs/tags/v0.3.0"]) == 1
    assert release.main(["notes", "0.2.0"]) == 0
    assert capsys.readouterr().out.strip().endswith("### Added\n- A thing (#3).")
    assert release.main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "0.2.0"


def test_prepare_dry_run_changes_nothing(repo, capsys):
    before = _git(repo, "rev-parse", "HEAD")
    assert release.main(["prepare", "patch", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Release v0.1.1 of demo-api" in out and "Dry run" in out
    assert _git(repo, "rev-parse", "HEAD") == before
    assert _git(repo, "status", "--porcelain") == ""
    assert _git(repo, "tag") == ""


def test_prepare_refuses_in_the_starter(repo, capsys):
    (repo / "pyproject.toml").write_text(PYPROJECT + STARTER_TABLE)
    _git(repo, "commit", "-q", "-am", "chore: mark as starter")
    _git(repo, "push", "-q")
    assert release.main(["prepare", "minor", "--skip-tests", "--no-push", "--yes"]) == 1
    assert "this is the starter" in capsys.readouterr().err
    assert _git(repo, "status", "--porcelain") == ""
    assert _git(repo, "tag") == ""
    assert (
        release.read_project((repo / "pyproject.toml").read_text()).version == "0.1.0"
    )


def test_prepare_refuses_off_main_dirty_or_behind(repo, capsys):
    _git(repo, "switch", "-q", "-c", "topic")
    assert release.main(["prepare", "minor", "--skip-tests", "--no-push", "--yes"]) == 1
    assert "cut from main" in capsys.readouterr().err
    _git(repo, "switch", "-q", "main")

    (repo / "scratch.txt").write_text("x")
    assert release.main(["prepare", "minor", "--skip-tests", "--no-push", "--yes"]) == 1
    assert "uncommitted" in capsys.readouterr().err
    (repo / "scratch.txt").unlink()

    other = repo.parent / "other"
    _git(repo.parent, "clone", "-q", str(repo.parent / "remote.git"), str(other))
    _git(other, "config", "user.email", "t@example.com")
    _git(other, "config", "user.name", "Test")
    (other / "note.txt").write_text("y")
    _git(other, "add", ".")
    _git(other, "commit", "-q", "-m", "docs: a note")
    _git(other, "push", "-q")
    assert release.main(["prepare", "minor", "--skip-tests", "--no-push", "--yes"]) == 1
    assert "behind" in capsys.readouterr().err
