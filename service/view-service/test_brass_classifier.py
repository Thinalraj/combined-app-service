import pytest

from brass_classifier import (
    BrassModelParams,
    CH1_F1_RULE_PARAMS,
    CH1_F3_RULE_PARAMS,
    CH2_F1_PARAMS,
    CH2_F3_PARAMS,
    brass_surface,
    calculate_session_scale,
    classify_brass,
    classify_brass_ch1_f1_ch1_f3,
    classify_brass_ch1_f1_ch2_f3,
    classify_brass_ch2_f1_f3,
    classify_brass_with_session_scale,
    generate_response_map,
    predict_brass_ch1_f1,
    residual_to_brass,
)


def test_sample_exactly_on_model_curve_is_high_confidence_brass():
    predicted = predict_brass_ch1_f1(16.7641, 0.27)
    result = classify_brass(16.7641, 0.27, predicted)
    assert result["label"] == "brass"
    assert result["confidence"] == "high"
    assert result["predicted_brass"] == pytest.approx(predicted)
    assert result["measured_response"] == pytest.approx(predicted)
    assert result["residual"] == pytest.approx(0.0)
    assert result["abs_residual"] == pytest.approx(0.0)
    assert result["within_calibrated_range"] is True
    assert result["warning"] is None


def test_residual_two_classifies_as_medium_confidence_brass():
    predicted = predict_brass_ch1_f1(16.7641, 0.27)
    result = classify_brass(16.7641, 0.27, predicted + 2.0)
    assert result["label"] == "brass"
    assert result["confidence"] == "medium"
    assert result["residual"] == pytest.approx(2.0)
    assert result["abs_residual"] == pytest.approx(2.0)


def test_residual_five_classifies_as_not_brass():
    predicted = predict_brass_ch1_f1(16.7641, 0.27)
    result = classify_brass(16.7641, 0.27, predicted + 5.0)
    assert result["label"] == "not_brass"
    assert result["confidence"] == "low"
    assert result["residual"] == pytest.approx(5.0)
    assert result["abs_residual"] == pytest.approx(5.0)


def test_negative_coverage_or_thickness_raises_value_error():
    with pytest.raises(ValueError):
        classify_brass(-16.7641, 0.27, 14.0)
    with pytest.raises(ValueError):
        classify_brass(16.7641, -0.27, 14.0)


def test_non_finite_response_raises_value_error():
    with pytest.raises(ValueError):
        classify_brass(16.7641, 0.27, float("nan"))


def test_outside_calibrated_range_returns_warning():
    result = classify_brass(5.0, 0.27, 14.0)
    assert result["within_calibrated_range"] is False
    assert "outside calibrated range" in result["warning"]


def test_residual_to_brass_uses_continuous_model():
    predicted = predict_brass_ch1_f1(25.0, 0.5)
    assert residual_to_brass(25.0, 0.5, predicted + 1.25) == pytest.approx(1.25)


def test_generate_response_map_returns_calculated_surface_points():
    points = generate_response_map(coverage_min=1.0, coverage_max=2.0, thickness_min=0.2, thickness_max=0.3, n=3)
    assert len(points) == 9
    assert set(points[0]) == {"coverage_pct", "thickness_mm", "predicted_brass"}


def test_session_scaling_changes_predicted_response_correctly():
    params = BrassModelParams()
    reference_predicted = predict_brass_ch1_f1(16.7641, 0.27, params)
    measured_reference = params.rmin + 0.75 * (reference_predicted - params.rmin)
    session_scale = calculate_session_scale(16.7641, 0.27, measured_reference, params)
    assert session_scale == pytest.approx(0.75)

    unscaled = predict_brass_ch1_f1(64.98, 0.127, params)
    expected_scaled = params.rmin + session_scale * (unscaled - params.rmin)
    result = classify_brass_with_session_scale(64.98, 0.127, expected_scaled, params=params, session_scale=session_scale)
    assert result["predicted_brass"] == pytest.approx(expected_scaled)
    assert result["session_scale"] == pytest.approx(session_scale)
    assert result["label"] == "brass"
    assert result["confidence"] == "high"


def test_ch2_two_feature_on_surface_is_high_confidence_brass():
    pred_f1 = brass_surface(64.96, 0.127, CH2_F1_PARAMS.rmin, CH2_F1_PARAMS.rspan, CH2_F1_PARAMS.k, CH2_F1_PARAMS.alpha, CH2_F1_PARAMS.d)
    pred_f3 = brass_surface(64.96, 0.127, CH2_F3_PARAMS.rmin, CH2_F3_PARAMS.rspan, CH2_F3_PARAMS.k, CH2_F3_PARAMS.alpha, CH2_F3_PARAMS.d)
    result = classify_brass_ch2_f1_f3(64.96, 0.127, pred_f1, pred_f3)
    assert result["label"] == "brass"
    assert result["confidence"] == "high"
    assert result["two_feature_distance"] == pytest.approx(0.0)


def test_ch2_two_feature_distance_less_than_two_is_high():
    pred_f1 = brass_surface(64.96, 0.127, CH2_F1_PARAMS.rmin, CH2_F1_PARAMS.rspan, CH2_F1_PARAMS.k, CH2_F1_PARAMS.alpha, CH2_F1_PARAMS.d)
    pred_f3 = brass_surface(64.96, 0.127, CH2_F3_PARAMS.rmin, CH2_F3_PARAMS.rspan, CH2_F3_PARAMS.k, CH2_F3_PARAMS.alpha, CH2_F3_PARAMS.d)
    result = classify_brass_ch2_f1_f3(64.96, 0.127, pred_f1 + CH2_F1_PARAMS.rmse, pred_f3)
    assert result["label"] == "brass"
    assert result["confidence"] == "high"
    assert result["two_feature_distance"] == pytest.approx(1.0)


def test_ch2_two_feature_distance_between_two_and_three_is_medium():
    pred_f1 = brass_surface(64.96, 0.127, CH2_F1_PARAMS.rmin, CH2_F1_PARAMS.rspan, CH2_F1_PARAMS.k, CH2_F1_PARAMS.alpha, CH2_F1_PARAMS.d)
    pred_f3 = brass_surface(64.96, 0.127, CH2_F3_PARAMS.rmin, CH2_F3_PARAMS.rspan, CH2_F3_PARAMS.k, CH2_F3_PARAMS.alpha, CH2_F3_PARAMS.d)
    result = classify_brass_ch2_f1_f3(64.96, 0.127, pred_f1 + (2.5 * CH2_F1_PARAMS.rmse), pred_f3)
    assert result["label"] == "brass_like"
    assert result["confidence"] == "medium"
    assert result["two_feature_distance"] == pytest.approx(2.5)


def test_ch2_two_feature_distance_greater_than_three_is_low():
    pred_f1 = brass_surface(64.96, 0.127, CH2_F1_PARAMS.rmin, CH2_F1_PARAMS.rspan, CH2_F1_PARAMS.k, CH2_F1_PARAMS.alpha, CH2_F1_PARAMS.d)
    pred_f3 = brass_surface(64.96, 0.127, CH2_F3_PARAMS.rmin, CH2_F3_PARAMS.rspan, CH2_F3_PARAMS.k, CH2_F3_PARAMS.alpha, CH2_F3_PARAMS.d)
    result = classify_brass_ch2_f1_f3(64.96, 0.127, pred_f1 + (3.5 * CH2_F1_PARAMS.rmse), pred_f3)
    assert result["label"] == "not_brass_or_outlier"
    assert result["confidence"] == "low"
    assert result["two_feature_distance"] == pytest.approx(3.5)


def test_ch2_two_feature_negative_geometry_raises_value_error():
    pred_f1 = 10.0
    pred_f3 = 10.0
    with pytest.raises(ValueError):
        classify_brass_ch2_f1_f3(64.96, -0.127, pred_f1, pred_f3)
    with pytest.raises(ValueError):
        classify_brass_ch2_f1_f3(-64.96, 0.127, pred_f1, pred_f3)


def test_ch2_two_feature_outside_range_returns_warning():
    result = classify_brass_ch2_f1_f3(5.0, 0.127, 10.0, 10.0)
    assert result["within_calibrated_range"] is False
    assert "outside calibrated geometry range" in result["warning"]


def test_fuzzy_ch1f1_ch1f3_on_surface_is_high_confidence_brass():
    pred_f1 = brass_surface(64.96, 0.127, CH1_F1_RULE_PARAMS.rmin, CH1_F1_RULE_PARAMS.rspan, CH1_F1_RULE_PARAMS.k, CH1_F1_RULE_PARAMS.alpha, CH1_F1_RULE_PARAMS.d)
    pred_f3 = brass_surface(64.96, 0.127, CH1_F3_RULE_PARAMS.rmin, CH1_F3_RULE_PARAMS.rspan, CH1_F3_RULE_PARAMS.k, CH1_F3_RULE_PARAMS.alpha, CH1_F3_RULE_PARAMS.d)
    result = classify_brass_ch1_f1_ch1_f3(64.96, 0.127, pred_f1, pred_f3)
    assert result["label"] == "brass"
    assert result["confidence"] == "high"
    assert result["mu_brass"] == pytest.approx(1.0)


def test_fuzzy_ch1f1_ch2f3_medium_membership():
    pred_f1 = brass_surface(64.96, 0.127, CH1_F1_RULE_PARAMS.rmin, CH1_F1_RULE_PARAMS.rspan, CH1_F1_RULE_PARAMS.k, CH1_F1_RULE_PARAMS.alpha, CH1_F1_RULE_PARAMS.d)
    pred_f3 = brass_surface(64.96, 0.127, CH2_F3_PARAMS.rmin, CH2_F3_PARAMS.rspan, CH2_F3_PARAMS.k, CH2_F3_PARAMS.alpha, CH2_F3_PARAMS.d)
    result = classify_brass_ch1_f1_ch2_f3(
        64.96,
        0.127,
        pred_f1 + (1.7 * CH1_F1_RULE_PARAMS.rmse),
        pred_f3,
    )
    assert result["label"] == "brass_like_uncertain"
    assert result["confidence"] == "medium"
    assert 0.40 <= result["mu_brass"] < 0.75


def test_fuzzy_ch1f1_ch2f3_low_membership_returns_not_brass():
    pred_f1 = brass_surface(64.96, 0.127, CH1_F1_RULE_PARAMS.rmin, CH1_F1_RULE_PARAMS.rspan, CH1_F1_RULE_PARAMS.k, CH1_F1_RULE_PARAMS.alpha, CH1_F1_RULE_PARAMS.d)
    pred_f3 = brass_surface(64.96, 0.127, CH2_F3_PARAMS.rmin, CH2_F3_PARAMS.rspan, CH2_F3_PARAMS.k, CH2_F3_PARAMS.alpha, CH2_F3_PARAMS.d)
    result = classify_brass_ch1_f1_ch2_f3(
        64.96,
        0.127,
        pred_f1 + (3.0 * CH1_F1_RULE_PARAMS.rmse),
        pred_f3,
    )
    assert result["label"] == "not_brass"
    assert result["confidence"] == "low"
    assert result["mu_brass"] == pytest.approx(0.0)
