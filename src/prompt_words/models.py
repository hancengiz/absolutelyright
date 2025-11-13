"""SQLAlchemy models for prompt words tracking."""
from sqlalchemy import Column, String, Integer, Text
from src.database import Base


class PromptWordCount(Base):
    """Model for daily prompt word counts per workstation."""

    __tablename__ = "prompt_word_counts"

    day = Column(String, primary_key=True)
    workstation_id = Column(String, primary_key=True)
    words = Column(Text, nullable=False, default="{}")
    total_user_messages = Column(Integer, default=0)

    def __repr__(self):
        return f"<PromptWordCount(day={self.day}, workstation_id={self.workstation_id}, total_user_messages={self.total_user_messages})>"
