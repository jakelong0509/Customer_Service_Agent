from datetime import datetime
from pydantic import BaseModel

class CustomerModel(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    address: str
    city: str
    state: str
    zip: str
    country: str
    created_at: datetime
    updated_at: datetime