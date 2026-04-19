from src.core.enums import ProviderName, GeneralStatus


class TestProviderName:
    def test_doctor(self):
        assert ProviderName.DOCTOR.value == "Doctor"

    def test_nurse(self):
        assert ProviderName.NURSE.value == "Nurse"

    def test_room(self):
        assert ProviderName.ROOM.value == "Room"

    def test_equipment(self):
        assert ProviderName.EQUIPMENT.value == "Equipment"

    def test_all_providers(self):
        assert len(ProviderName) == 4


class TestGeneralStatus:
    def test_pending(self):
        assert GeneralStatus.PENDING.value == "pending"

    def test_scheduled(self):
        assert GeneralStatus.SCHEDULED.value == "scheduled"

    def test_completed(self):
        assert GeneralStatus.COMPLETED.value == "completed"

    def test_cancelled(self):
        assert GeneralStatus.CANCELLED.value == "cancelled"

    def test_all_statuses(self):
        assert len(GeneralStatus) == 4
