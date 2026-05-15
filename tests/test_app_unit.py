import pytest
from infisical_conf.app import InfisicalManager


# -------------------------------------------------------------------
# _booler() tests
# -------------------------------------------------------------------

def test_booler_truthy():


    m = InfisicalManager(log_level="ERROR", redact=True, visuals=False)
    assert m._booler(True) is True
    assert m._booler(1) is True
    assert m._booler("on") is True
    assert m._booler("ENABLED") is True


def test_booler_falsy():


    m = InfisicalManager(log_level="ERROR", redact=True, visuals=False)
    assert m._booler(False) is False
    assert m._booler(0) is False
    assert m._booler("off") is False
    assert m._booler("DISABLED") is False


def test_booler_invalid():


    m = InfisicalManager(log_level="ERROR", redact=True, visuals=False)
    with pytest.raises(ValueError):
        m._booler("maybe")


# -------------------------------------------------------------------
# set_env() tests
# -------------------------------------------------------------------

def test_set_env(monkeypatch):
    monkeypatch.setenv("INFISICAL_HOST", "http://dummy")
    monkeypatch.setenv("INFISICAL_CLIENT_ID", "id")
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "secret")

    monkeypatch.setattr(InfisicalManager, "_authenticate", lambda self: None)
    monkeypatch.setattr(InfisicalManager, "pull_projects_list", lambda self: None)


    m = InfisicalManager(log_level="ERROR", redact=True, visuals=False)
    m.set_env("dev")
    assert m.default_env == "dev"


def test_set_env_default(monkeypatch):
    monkeypatch.setenv("INFISICAL_HOST", "http://dummy")
    monkeypatch.setenv("INFISICAL_CLIENT_ID", "id")
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "secret")

    monkeypatch.setattr(InfisicalManager, "_authenticate", lambda self: None)
    monkeypatch.setattr(InfisicalManager, "pull_projects_list", lambda self: None)

    m = InfisicalManager(log_level="ERROR", redact=True, visuals=False)
    m.set_env(None)
    assert m.default_env == "prod"


# -------------------------------------------------------------------
# set_visuals(), set_tree_tags(), set_tree_notes()
# -------------------------------------------------------------------

def test_set_visuals(monkeypatch):
    monkeypatch.setenv("INFISICAL_HOST", "http://dummy")
    monkeypatch.setenv("INFISICAL_CLIENT_ID", "id")
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "secret")
    monkeypatch.setattr(InfisicalManager, "_authenticate", lambda self: None)
    monkeypatch.setattr(InfisicalManager, "pull_projects_list", lambda self: None)


    m = InfisicalManager(log_level="ERROR", redact=True, visuals=False)
    assert m.set_visuals("on") is True
    assert m.set_visuals("off") is False


def test_set_tree_tags(monkeypatch):
    monkeypatch.setenv("INFISICAL_HOST", "http://dummy")
    monkeypatch.setenv("INFISICAL_CLIENT_ID", "id")
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "secret")

    monkeypatch.setattr(InfisicalManager, "_authenticate", lambda self: None)
    monkeypatch.setattr(InfisicalManager, "pull_projects_list", lambda self: None)


    m = InfisicalManager(log_level="ERROR", redact=True, visuals=False)
    assert m.set_tree_tags("enabled") is True
    assert m.set_tree_tags("disabled") is False


def test_set_tree_notes(monkeypatch):
    monkeypatch.setenv("INFISICAL_HOST", "http://dummy")
    monkeypatch.setenv("INFISICAL_CLIENT_ID", "id")
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "secret")

    monkeypatch.setattr(InfisicalManager, "_authenticate", lambda self: None)
    monkeypatch.setattr(InfisicalManager, "pull_projects_list", lambda self: None)


    m = InfisicalManager(log_level="ERROR", redact=True, visuals=False)
    assert m.set_tree_notes("on") is True
    assert m.set_tree_notes("off") is False
