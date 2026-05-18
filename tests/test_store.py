from __future__ import annotations

from pathlib import Path

from owl_cli.store import Store, project_home, project_root, user_home


def test_store_defaults_runtime_home_to_current_project(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OWL_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)

    assert project_root() == tmp_path
    assert project_home() == tmp_path / ".owl"
    assert Store().home == tmp_path / ".owl"


def test_owl_project_root_controls_runtime_home(tmp_path: Path, monkeypatch) -> None:
    user = tmp_path / "user"
    project = tmp_path / "project"
    monkeypatch.setenv("OWL_HOME", str(user))
    monkeypatch.setenv("OWL_PROJECT_ROOT", str(project))

    assert user_home() == user
    assert project_root() == project
    assert Store().home == project / ".owl"
