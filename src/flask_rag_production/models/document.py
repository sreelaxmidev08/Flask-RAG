from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from flask_rag_production.models import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    source: Mapped[str] = mapped_column(
        String(100)
    )

    version: Mapped[str] = mapped_column(
        String(50)
    )

    title: Mapped[str] = mapped_column(
        String(500)
    )

    source_file: Mapped[str] = mapped_column(
        String(500)
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )