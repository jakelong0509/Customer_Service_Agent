import pytest
from unittest.mock import patch, MagicMock
from src.services.skill_registry import SkillRecord, get_skills, get_skill_tools


class TestSkillRecord:
    def test_create_skill_record_defaults(self):
        record = SkillRecord(
            name="test_skill",
            description="A test skill",
            when_to_use="When testing",
            isolation_fork=False,
            body="Skill body content",
        )
        assert record.name == "test_skill"
        assert record.active is False
        assert record.body == "Skill body content"
        assert record.isolation_fork is False

    def test_skill_record_active_toggle(self):
        record = SkillRecord(
            name="test_skill",
            description="desc",
            when_to_use="testing",
            isolation_fork=False,
            body="body",
        )
        assert record.active is False
        record.active = True
        assert record.active is True
        record.active = False
        assert record.active is False

    def test_skill_record_isolation_fork_true(self):
        record = SkillRecord(
            name="iso_skill",
            description="desc",
            when_to_use="testing",
            isolation_fork=True,
            body="body",
        )
        assert record.isolation_fork is True


class TestGetSkills:
    def test_load_appointment_booking_skill(self):
        with patch("src.services.skill_registry._parse_skill_md") as mock_parse:
            mock_parse.return_value = SkillRecord(
                name="appointment_booking_skill",
                description="Voice/agent workflow for clinic-style appointment scheduling",
                when_to_use="when booking appointments",
                isolation_fork=False,
                body="# Appointment booking skill\n\nGuidance...",
            )
            skills = get_skills(["appointment_booking_skill"])
            assert "appointment_booking_skill" in skills
            skill = skills["appointment_booking_skill"]
            assert skill.name == "appointment_booking_skill"
            assert skill.description != ""
            assert skill.active is False

    def test_load_email_skill(self):
        with patch("src.services.skill_registry._parse_skill_md") as mock_parse:
            mock_parse.return_value = SkillRecord(
                name="email_skill",
                description="Use this skill for email",
                when_to_use="when handling email",
                isolation_fork=False,
                body="# Email skill",
            )
            skills = get_skills(["email_skill"])
            assert "email_skill" in skills
            skill = skills["email_skill"]
            assert skill.name == "email_skill"
            assert "email" in skill.description.lower()

    def test_load_multiple_skills(self):
        with patch("src.services.skill_registry._parse_skill_md") as mock_parse:
            mock_parse.side_effect = [
                SkillRecord(name="appointment_booking_skill", description="desc1", when_to_use="a", isolation_fork=False, body="body1"),
                SkillRecord(name="email_skill", description="desc2", when_to_use="b", isolation_fork=False, body="body2"),
            ]
            skills = get_skills(["appointment_booking_skill", "email_skill"])
            assert len(skills) == 2
            assert "appointment_booking_skill" in skills
            assert "email_skill" in skills

    def test_load_nonexistent_skill_raises(self):
        with pytest.raises(FileNotFoundError, match="nonexistent_skill"):
            get_skills(["nonexistent_skill"])

    def test_skills_start_inactive(self):
        with patch("src.services.skill_registry._parse_skill_md") as mock_parse:
            mock_parse.side_effect = [
                SkillRecord(name="appointment_booking_skill", description="d", when_to_use="a", isolation_fork=False, body="b"),
                SkillRecord(name="email_skill", description="d", when_to_use="a", isolation_fork=False, body="b"),
            ]
            skills = get_skills(["appointment_booking_skill", "email_skill"])
            for skill in skills.values():
                assert skill.active is False


class TestGetSkillTools:
    def test_get_appointment_booking_tools(self):
        mock_tools = [MagicMock(name="create_appointment_resource_booking"),
                      MagicMock(name="select_appointment_resource_bookings"),
                      MagicMock(name="select_providers"),
                      MagicMock(name="select_slot_templates")]
        mock_tools[0].name = "create_appointment_resource_booking"
        mock_tools[1].name = "select_appointment_resource_bookings"
        mock_tools[2].name = "select_providers"
        mock_tools[3].name = "select_slot_templates"

        mock_mod = MagicMock()
        mock_mod.get_tools.return_value = mock_tools

        with patch("importlib.import_module", return_value=mock_mod):
            tools = get_skill_tools(["appointment_booking_skill"])
            assert len(tools) == 4
            tool_names = [t.name for t in tools]
            assert "create_appointment_resource_booking" in tool_names
            assert "select_appointment_resource_bookings" in tool_names
            assert "select_providers" in tool_names
            assert "select_slot_templates" in tool_names

    def test_get_email_skill_tools(self):
        mock_mod = MagicMock()
        mock_mod.get_tools.return_value = [MagicMock()]

        with patch("importlib.import_module", return_value=mock_mod):
            tools = get_skill_tools(["email_skill"])
            assert isinstance(tools, list)

    def test_get_multiple_skill_tools(self):
        mock_mod_1 = MagicMock()
        mock_mod_1.get_tools.return_value = [MagicMock(), MagicMock()]
        mock_mod_2 = MagicMock()
        mock_mod_2.get_tools.return_value = [MagicMock()]

        with patch("importlib.import_module", side_effect=[mock_mod_1, mock_mod_2]):
            tools = get_skill_tools(["appointment_booking_skill", "email_skill"])
            assert len(tools) >= 3

    def test_get_tools_empty_list(self):
        tools = get_skill_tools([])
        assert tools == []
