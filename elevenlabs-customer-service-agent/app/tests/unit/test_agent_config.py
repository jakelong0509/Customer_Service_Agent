from src.core.agent_config import load_agent_configs


class TestLoadAgentConfigs:
    def test_loads_all_agents(self):
        configs = load_agent_configs()
        assert len(configs) == 4

    def test_customer_support_agent_config(self):
        configs = load_agent_configs()
        csa = next(c for c in configs if c["name"] == "customer_support_agent")
        assert csa["communication_type"] == "voice"
        assert "appointment_booking_skill" in csa["skill_names"]
        assert "email_skill" in csa["skill_names"]
        assert csa["llm"] == "kimi-k2.5"

    def test_customer_support_email_agent_config(self):
        configs = load_agent_configs()
        csa_email = next(c for c in configs if c["name"] == "customer_support_agent_email")
        assert csa_email["communication_type"] == "email"
        assert "appointment_booking_skill" in csa_email["skill_names"]

    def test_security_agent_config(self):
        configs = load_agent_configs()
        sec = next(c for c in configs if c["name"] == "security_agent")
        assert sec["communication_type"] == "chat"
        assert sec["skill_names"] == []
        assert sec["state_class"] is not None

    def test_rxnorm_agent_config(self):
        configs = load_agent_configs()
        rx = next(c for c in configs if c["name"] == "rxnorm_mapping_agent_email")
        assert rx["communication_type"] == "email"
        assert "text_normalize_skill" in rx["skill_names"]
        assert "clinical_entity_extraction_skill" in rx["skill_names"]
        assert "rxnorm_mapping_skill" in rx["skill_names"]

    def test_all_agents_have_system_prompt(self):
        configs = load_agent_configs()
        for config in configs:
            assert "system_prompt_path" in config
            assert config["system_prompt_path"].endswith(".md")

    def test_all_agents_have_tools(self):
        configs = load_agent_configs()
        for config in configs:
            assert len(config["tools"]) > 0
            assert "activate_skill" in config["tools"]
            assert "deactivate_skill" in config["tools"]

    def test_all_agents_have_db_uri(self):
        configs = load_agent_configs()
        for config in configs:
            assert config["db_uri"] == "POSTGRES_CONNECTION_STRING"
