import pytest


def pytest_addoption(parser):
    parser.addoption("--run-models", action="store_true", default=False,
                     help="Run integration tests that can download CLIP model weights")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-models"):
        return
    skip = pytest.mark.skip(reason="Model integration requires explicit --run-models")
    for item in items:
        if "model_integration" in item.keywords:
            item.add_marker(skip)
