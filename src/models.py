"""SQLAlchemy models for the application."""
from sqlalchemy import Column, String, Integer, Text
from src.database import Base


class DayCount(Base):
    """Model for daily pattern counts."""

    __tablename__ = "day_counts"

    day = Column(String, primary_key=True, index=True)
    patterns = Column(Text, nullable=False, default="{}")
    total_messages = Column(Integer, default=0)

    def __repr__(self):
        return f"<DayCount(day={self.day}, total_messages={self.total_messages})>"
