import pytest
from infisical_conf.notation import NotationMixin

class Dummy(NotationMixin):
    pass

def test_valid_notation():
    d = Dummy()
    assert d._validate_notation("proj.folder.key") is True
    assert d._validate_notation("proj.folder.*") is True
    assert d._validate_notation("proj.*.*") is True

def test_invalid_notation():
    d = Dummy()
    with pytest.raises(ValueError):
        d._validate_notation("*.folder.*")

    with pytest.raises(ValueError):
        d._validate_notation("project.*.secret")