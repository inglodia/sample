from pydantic import BaseModel


class SignupDay(BaseModel):
    date: str
    count: int


class DashboardStats(BaseModel):
    total_users: int
    new_users_30d: int
    admin_count: int
    user_count: int
    signups_by_day: list[SignupDay]
