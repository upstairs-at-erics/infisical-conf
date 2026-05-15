import pytest
from unittest.mock import MagicMock

from infisical_conf.api import APIMixin


# -------------------------------------------------------------------
# FIXTURE: a clean APIMixin instance with required attributes
# -------------------------------------------------------------------

@pytest.fixture
def api():
    """
    Provide a clean APIMixin instance with the minimum attributes
    required for testing without hitting the network.
    """
    m = APIMixin()
    m.host = "http://dummy"
    m.accesstoken = "abc"
    m.visuals = False
    return m


# -------------------------------------------------------------------
# TEST: _build_project_meta_cache()
# -------------------------------------------------------------------

def test_build_project_meta_cache(api):
    projects = [
        {
            "slug": "proj1",
            "type": "personal",
            "id": "123",
            "environments": [{"slug": "dev"}, {"slug": "prod"}]
        },
        {
            "slug": "proj2",
            "type": "team",
            "id": "456",
            "environments": [{"slug": "stage"}]
        }
    ]

    meta = api._build_project_meta_cache(projects)

    assert "proj1" in meta
    assert meta["proj1"]["type"] == "personal"
    assert meta["proj1"]["id"] == "123"
    assert meta["proj1"]["environments"] == ["dev", "prod"]

    assert "proj2" in meta
    assert meta["proj2"]["type"] == "team"
    assert meta["proj2"]["id"] == "456"
    assert meta["proj2"]["environments"] == ["stage"]


# -------------------------------------------------------------------
# TEST: _get_project_id() success
# -------------------------------------------------------------------

def test_get_project_id_success(api):
    api._project_meta_cache = {
        "proj1": {"id": "123"}
    }

    assert api._get_project_id("proj1") == "123"


# -------------------------------------------------------------------
# TEST: _get_project_id() failure
# -------------------------------------------------------------------

def test_get_project_id_unknown(api):
    api._project_meta_cache = {}

    with pytest.raises(ValueError):
        api._get_project_id("missing")


# -------------------------------------------------------------------
# TEST: pull_projects_list() with mocked requests.get
# -------------------------------------------------------------------

def test_pull_projects_list(monkeypatch, api):
    fake_json = {
        "projects": [
            {
                "slug": "proj1",
                "type": "personal",
                "id": "123",
                "environments": [{"slug": "dev"}]
            }
        ]
    }

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return fake_json

    # Mock requests.get so no network call is made
    monkeypatch.setattr("requests.get", lambda *args, **kwargs: FakeResponse())

    meta = api.pull_projects_list()

    assert "proj1" in meta
    assert meta["proj1"]["id"] == "123"
    assert meta["proj1"]["environments"] == ["dev"]


# -------------------------------------------------------------------
# TEST: pull_projects_list() returns cached data on second call
# -------------------------------------------------------------------

def test_pull_projects_list_uses_cache(monkeypatch, api):
    """
    First call populates cache.
    Second call must NOT call requests.get again.
    """

    fake_json = {
        "projects": [
            {
                "slug": "proj1",
                "type": "personal",
                "id": "123",
                "environments": [{"slug": "dev"}]
            }
        ]
    }

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return fake_json

    mock_get = MagicMock(return_value=FakeResponse())
    monkeypatch.setattr("requests.get", mock_get)

    # First call populates cache
    api.pull_projects_list()

    # Second call should use cache, not call requests.get
    api.pull_projects_list()

    # Ensure requests.get was called only once
    assert mock_get.call_count == 1
