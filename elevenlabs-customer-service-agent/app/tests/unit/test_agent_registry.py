from src.services.agent_registry import AgentRegistry, _load_state_class
from src.core.agent_state import AgentState


class TestAgentRegistry:
    def test_register_and_get(self):
        registry = AgentRegistry()

        class DummyAgent:
            pass

        registry.register("test", DummyAgent)
        assert registry.get("test") is DummyAgent

    def test_register_duplicate_raises(self):
        registry = AgentRegistry()

        class Agent1:
            pass

        registry.register("dup_name", Agent1)
        try:
            registry.register("dup_name", Agent1)
            assert False, "Expected ValueError"
        except ValueError:
            pass

    def test_get_missing_returns_none(self):
        registry = AgentRegistry()
        assert registry.get("nonexistent") is None

    def test_contains(self):
        registry = AgentRegistry()

        class A:
            pass

        registry.register("a", A)
        assert "a" in registry
        assert "b" not in registry

    def test_names_sorted(self):
        registry = AgentRegistry()

        class B:
            pass

        class A:
            pass

        registry.register("beta", B)
        registry.register("alpha", A)
        assert registry.names() == ("alpha", "beta")

    def test_clear(self):
        registry = AgentRegistry()

        class A:
            pass

        registry.register("a", A)
        registry.clear()
        assert registry.get("a") is None

    def test_items_sorted(self):
        registry = AgentRegistry()

        class B:
            pass

        class A:
            pass

        registry.register("beta", B)
        registry.register("alpha", A)
        items = registry.items()
        assert items[0][0] == "alpha"
        assert items[1][0] == "beta"


class TestLoadStateClass:
    def test_none_returns_base_state(self):
        result = _load_state_class(None)
        assert result is AgentState

    def test_empty_string_returns_base_state(self):
        result = _load_state_class("")
        assert result is AgentState

    def test_load_custom_state_class(self):
        result = _load_state_class(
            "src.agents.security_agent.state.SecurityAgentState"
        )
        from src.agents.security_agent.state import SecurityAgentState

        assert result is SecurityAgentState

    def test_load_rxnorm_state_class(self):
        result = _load_state_class(
            "src.agents.rxnorm_mapping_agent.state.RxNormAgentState"
        )
        from src.agents.rxnorm_mapping_agent.state import RxNormAgentState

        assert result is RxNormAgentState
