from datetime import datetime
from pydantic import BaseModel, Field

class CustomerModel(BaseModel):
    id: str
    phone: str = Field(..., description="Caller phone number")
    email: str = Field(..., description="Caller email")
    name: str = Field(..., description="Caller name")
    plan: str = Field(..., description="Caller plan")
    status: str = Field(..., description="Caller status")