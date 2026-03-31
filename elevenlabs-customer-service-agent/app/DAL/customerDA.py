from src.core.customer import CustomerModel
from src.infrastructure.database import fetchrow


class CustomerDA:
    async def get_customer_by_phone_number(self, phone_number: str) -> CustomerModel | None:
        row = await fetchrow(
            "SELECT id, phone, email, name, plan, status FROM customers WHERE phone = $1",
            phone_number,
        )
        if row is None:
            return None
        return CustomerModel(
            id=str(row["id"]),
            phone=row["phone"],
            email=row["email"],
            name=row["name"],
            plan=row["plan"],
            status=row["status"],
        )

    async def create_customer(self, customer: CustomerModel) -> CustomerModel:
        row = await fetchrow(
            "INSERT INTO customers (phone, email, name, plan, status) VALUES ($1, $2, $3, $4, $5) RETURNING *",
            customer.phone,
            customer.email,
            customer.name,
            customer.plan,
            customer.status,
        )
        if row is None:
            return None
        return CustomerModel(
            id=str(row["id"]),
            phone=row["phone"],
            email=row["email"],
            name=row["name"],
            plan=row["plan"],
            status=row["status"],
        )