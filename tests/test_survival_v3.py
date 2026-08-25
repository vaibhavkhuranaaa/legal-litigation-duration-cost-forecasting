from pathlib import Path

import numpy as np
import pytest

from litigation_planner.survival_v3 import (
    _certify_keys,
    fit_positive_logit_affine,
    positive_logit_affine,
    run_development_evaluation,
)


def test_positive_logit_affine_preserves_probability_order() -> None:
    probabilities = np.asarray([[0.1, 0.3, 0.8]], dtype=np.float32)

    calibrated = positive_logit_affine(probabilities, intercept=0.4, log_slope=-0.2)

    assert np.all(np.diff(calibrated[0]) > 0)
    assert np.all((calibrated > 0) & (calibrated < 1))


def test_positive_logit_fit_improves_shifted_validation_probabilities() -> None:
    probabilities = np.tile(np.asarray([[0.2, 0.5]], dtype=np.float32), (400, 1))
    outcomes = np.tile(np.asarray([[0.4, 0.7]], dtype=np.float32), (400, 1))

    parameters = fit_positive_logit_affine(probabilities, outcomes)
    calibrated = positive_logit_affine(probabilities, *parameters)

    assert np.square(calibrated - outcomes).mean() < np.square(probabilities - outcomes).mean()


def test_support_certification_requires_count_and_calibration() -> None:
    good = ("exact", "1", "civil_rights", "3", "1")
    small = ("nature", "other")
    keys = [good] * 200 + [small] * 199
    probabilities = np.asarray([[0.4, 0.7]] * 399, dtype=np.float32)
    outcomes = np.asarray([[False, True]] * 399)

    certified = _certify_keys(keys, probabilities, outcomes, 200, 0.5)

    assert certified == {good}


def test_v3_development_evaluation_rejects_public_output() -> None:
    with pytest.raises(ValueError, match="outside public repository"):
        run_development_evaluation(
            Path("missing.duckdb"), Path("config/survival-v3.toml"), Path("tmp/v3.json")
        )
