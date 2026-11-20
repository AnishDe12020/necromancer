import os, sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from necro import registry

@pytest.fixture(scope="session")
def checks():
    mod = os.environ.get("NECRO_IMPL")
    if not mod:
        pytest.fail("set NECRO_IMPL=<module> to the implementation under test")
    _, checks = registry.load(mod)
    return checks

@pytest.fixture
def element(checks):
    def run(eid, text):
        fns = checks.get(eid)
        if not fns:
            pytest.fail(f"UNIMPLEMENTED {eid}: {text}", pytrace=False)
        for fn in fns:
            fn()
    return run
