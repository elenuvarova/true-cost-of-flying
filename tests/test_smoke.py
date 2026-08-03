"""Smoke test: the batch venv can import what the offline scripts need."""


def test_batch_deps_import():
    import numpy
    import pandas

    assert pandas.__version__
    assert numpy.__version__
