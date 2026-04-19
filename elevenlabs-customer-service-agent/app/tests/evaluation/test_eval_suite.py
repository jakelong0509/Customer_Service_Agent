"""Evaluation tests for agent workflow quality.

These tests use the evaluation dataset and helpers to measure agent output
quality. They can run against live agents (integration) or with mocked LLM
responses (unit-level evaluation framework validation).

Marked with @pytest.mark.evaluation so they can be run separately.
"""
import pytest
from tests.evaluation.eval_dataset import EVAL_CASES, MULTI_TURN_SCENARIOS
from tests.evaluation.eval_helpers import (
    assert_response_contains_topics,
    assert_response_excludes,
    compute_topic_coverage,
    compute_skill_activation_accuracy,
    compute_tool_selection_accuracy,
    check_response_is_helpful,
    compute_eval_score,
)


class TestEvalHelpers:
    def test_topic_coverage_all_present(self):
        response = "Your appointment is confirmed for Monday at 10 AM with Dr. Smith."
        missing = assert_response_contains_topics(response, ["appointment", "Monday", "Dr. Smith"])
        assert missing == []

    def test_topic_coverage_some_missing(self):
        response = "Your appointment is confirmed."
        missing = assert_response_contains_topics(response, ["appointment", "Monday", "Dr. Smith"])
        assert "Monday" in missing
        assert "Dr. Smith" in missing
        assert "appointment" not in missing

    def test_topic_coverage_score(self):
        response = "Your appointment is confirmed for Monday."
        score = compute_topic_coverage(response, ["appointment", "Monday", "Dr. Smith"])
        assert score == pytest.approx(2.0 / 3.0, abs=0.01)

    def test_topic_coverage_empty_topics(self):
        assert compute_topic_coverage("any response", []) == 1.0

    def test_excluded_terms_none_found(self):
        response = "Your appointment is confirmed."
        found = assert_response_excludes(response, ["Error", "cannot help"])
        assert found == []

    def test_excluded_terms_some_found(self):
        response = "Error: Something went wrong"
        found = assert_response_excludes(response, ["Error", "cannot"])
        assert "Error" in found

    def test_skill_activation_perfect(self):
        result = compute_skill_activation_accuracy(
            actual_skills=["appointment_booking_skill", "email_skill"],
            expected_skills=["appointment_booking_skill", "email_skill"],
        )
        assert result["precision"] == 1.0
        assert result["recall"] == 1.0
        assert result["f1"] == 1.0
        assert result["false_positives"] == []
        assert result["false_negatives"] == []

    def test_skill_activation_partial(self):
        result = compute_skill_activation_accuracy(
            actual_skills=["appointment_booking_skill"],
            expected_skills=["appointment_booking_skill", "email_skill"],
        )
        assert result["precision"] == 1.0
        assert result["recall"] == 0.5
        assert result["f1"] == pytest.approx(2 / 3, abs=0.01)
        assert "email_skill" in result["false_negatives"]

    def test_skill_activation_no_match(self):
        result = compute_skill_activation_accuracy(
            actual_skills=["email_skill"],
            expected_skills=["appointment_booking_skill"],
        )
        assert result["precision"] == 0.0
        assert result["recall"] == 0.0
        assert result["f1"] == 0.0
        assert "email_skill" in result["false_positives"]
        assert "appointment_booking_skill" in result["false_negatives"]

    def test_skill_activation_both_empty(self):
        result = compute_skill_activation_accuracy([], [])
        assert result["precision"] == 0.0
        assert result["recall"] == 1.0

    def test_helpfulness_good_response(self):
        result = check_response_is_helpful("Your appointment has been booked for Monday at 10 AM.")
        assert result["has_content"] is True
        assert result["not_error"] is True
        assert result["not_empty"] is True
        assert result["reasonable_length"] is True

    def test_helpfulness_error_response(self):
        result = check_response_is_helpful("Error: Agent not found")
        assert result["not_error"] is False

    def test_helpfulness_empty_response(self):
        result = check_response_is_helpful("")
        assert result["not_empty"] is False
        assert result["has_content"] is False

    def test_comprehensive_eval_score(self):
        score = compute_eval_score(
            response="Your appointment with Dr. Smith is confirmed for Monday at 10 AM.",
            expected_topics=["appointment", "Dr. Smith", "Monday"],
            excluded_terms=["Error"],
            actual_skills=["appointment_booking_skill"],
            expected_skills=["appointment_booking_skill"],
            actual_tools=["activate_skill"],
            expected_tools=["activate_skill"],
        )
        assert score["overall_score"] > 0.8
        assert score["topic_coverage"] == 1.0
        assert score["skill_metrics"]["f1"] == 1.0
        assert score["tool_metrics"]["f1"] == 1.0

    def test_comprehensive_eval_score_poor(self):
        score = compute_eval_score(
            response="Error: Something went wrong",
            expected_topics=["appointment"],
            excluded_terms=["Error"],
            actual_skills=[],
            expected_skills=["appointment_booking_skill"],
            actual_tools=[],
            expected_tools=["activate_skill"],
        )
        assert score["overall_score"] < 0.5
        assert score["excluded_violations"] == ["Error"]


class TestEvalDataset:
    def test_all_cases_have_ids(self):
        for case in EVAL_CASES:
            assert "id" in case
            assert case["id"].startswith("eval_")

    def test_all_cases_have_agents(self):
        valid_agents = {
            "customer_support_agent",
            "customer_support_agent_email",
            "security_agent",
            "rxnorm_mapping_agent_email",
        }
        for case in EVAL_CASES:
            assert case["agent"] in valid_agents, f"Case {case['id']} has invalid agent: {case['agent']}"

    def test_all_cases_have_communication_type(self):
        valid_types = {"voice", "email", "chat"}
        for case in EVAL_CASES:
            assert case["communication_type"] in valid_types

    def test_all_cases_have_category(self):
        for case in EVAL_CASES:
            assert "category" in case
            assert len(case["category"]) > 0

    def test_all_cases_have_input(self):
        for case in EVAL_CASES:
            assert len(case["input"]) > 0

    def test_multi_turn_scenarios_have_turns(self):
        for scenario in MULTI_TURN_SCENARIOS:
            assert len(scenario["turns"]) >= 2
            for turn in scenario["turns"]:
                assert "input" in turn
                assert "expected_response_topics" in turn


class TestEvalDatasetCoverage:
    def test_covers_all_agents(self):
        agents_covered = {case["agent"] for case in EVAL_CASES}
        expected_agents = {
            "customer_support_agent",
            "customer_support_agent_email",
            "security_agent",
            "rxnorm_mapping_agent_email",
        }
        assert expected_agents.issubset(agents_covered)

    def test_covers_appointment_categories(self):
        categories = {case["category"] for case in EVAL_CASES}
        appointment_categories = {"appointment_booking", "appointment_reschedule", "appointment_cancel"}
        assert appointment_categories.issubset(categories)

    def test_covers_communication_types(self):
        types = {case["communication_type"] for case in EVAL_CASES}
        assert "voice" in types
        assert "email" in types
        assert "chat" in types
