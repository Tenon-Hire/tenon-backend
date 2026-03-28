"""Application module for recruiters repositories companies recruiters companies core model workflows."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base, TimestampMixin


class Company(Base, TimestampMixin):
    """Company that owns simulations and users."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    users = relationship("User", back_populates="company")
    simulations = relationship("Simulation", back_populates="company")
