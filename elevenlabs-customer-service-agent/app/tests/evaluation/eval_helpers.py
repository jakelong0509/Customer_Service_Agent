"""Helper utilities for evaluating agent responses.

Provides assertion functions, scoring helpers, and LLM-as-judge utilities
for measuring agent output quality against expected outcomes.
"""
from typing import List


def assert_response_contains_topics(response: str, topics: List[str]) -> List[str]:
    """Check that the response contains at least one reference to each topic.
    
    Returns list of missing topics.
    """
    response_lower = response.lower()
    missing = []
    for topic in topics:
        if topic.lower() not in response_lower:
            missing.append(topic)
    return missing


def assert_response_excludes(response: str, excluded: List[str]) -> List[str]:
    """Check that the response does NOT contain excluded terms.
    
    Returns list of found excluded terms.
    """
    response_lower = response.lower()
    found = []
    for term in excluded:
        if term.lower() in response_lower:
            found.append(term)
    return found


def compute_topic_coverage(response: str, expected_topics: List[str]) -> float:
    """Compute the fraction of expected topics present in the response.
    
    Returns a value between 0.0 and 1.0.
    """
    if not expected_topics:
        return 1.0
    missing = assert_response_contains_topics(response, expected_topics)
    return 1.0 - (len(missing) / len(expected_topics))


def compute_skill_activation_accuracy(
    actual_skills: List[str],
    expected_skills: List[str],
) -> dict:
    """Compute precision, recall, and F1 for skill activation.
    
    Args:
        actual_skills: Skills that were actually activated.
        expected_skills: Skills that should have been activated.
    
    Returns dict with precision, recall, f1, false_positives, false_negatives.
    """
    actual_set = set(actual_skills)
    expected_set = set(expected_skills)

    true_positives = actual_set & expected_set
    false_positives = actual_set - expected_set
    false_negatives = expected_set - actual_set

    precision = len(true_positives) / len(actual_set) if actual_set else 0.0
    recall = len(true_positives) / len(expected_set) if expected_set else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": list(true_positives),
        "false_positives": list(false_positives),
        "false_negatives": list(false_negatives),
    }


def compute_tool_selection_accuracy(
    actual_tools: List[str],
    expected_tools: List[str],
) -> dict:
    """Compute accuracy metrics for tool selection.
    
    Returns dict with precision, recall, f1.
    """
    return compute_skill_activation_accuracy(actual_tools, expected_tools)


def check_response_is_helpful(response: str) -> dict:
    """Heuristic check for response helpfulness.
    
    Returns dict with boolean flags for various quality signals.
    """
    response_lower = response.lower()
    return {
        "has_content": len(response.strip()) > 10,
        "not_error": not response.lower().startswith("error:"),
        "not_empty": len(response.strip()) > 0,
        "reasonable_length": 10 < len(response) < 5000,
    }


def compute_eval_score(
    response: str,
    expected_topics: List[str],
    excluded_terms: List[str],
    actual_skills: List[str],
    expected_skills: List[str],
    actual_tools: List[str],
    expected_tools: List[str],
) -> dict:
    """Compute a comprehensive evaluation score for an agent response.
    
    Returns dict with all metrics.
    """
    topic_coverage = compute_topic_coverage(response, expected_topics)
    excluded_violations = assert_response_excludes(response, excluded_terms)
    skill_metrics = compute_skill_activation_accuracy(actual_skills, expected_skills)
    tool_metrics = compute_tool_selection_accuracy(actual_tools, expected_tools)
    helpfulness = check_response_is_helpful(response)

    overall_score = (
        topic_coverage * 0.3
        + skill_metrics["f1"] * 0.3
        + tool_metrics["f1"] * 0.2
        + (1.0 if helpfulness["not_error"] else 0.0) * 0.1
        + (1.0 if not excluded_violations else 0.0) * 0.1
    )

    return {
        "overall_score": overall_score,
        "topic_coverage": topic_coverage,
        "topic_missing": assert_response_contains_topics(response, expected_topics),
        "excluded_violations": excluded_violations,
        "skill_metrics": skill_metrics,
        "tool_metrics": tool_metrics,
        "helpfulness": helpfulness,
    }
