from enum import Enum
class ProviderName(Enum):
  DOCTOR = "Doctor"
  NURSE = "Nurse"
  ROOM = "Room"
  EQUIPMENT = "Equipment"

class GeneralStatus(Enum):
  PENDING = "pending"
  SCHEDULED = "scheduled"
  COMPLETED = "completed"
  CANCELLED = "cancelled"