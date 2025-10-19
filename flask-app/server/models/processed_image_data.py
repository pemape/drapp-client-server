from server.database import db
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum

class ProcessingStatus(Enum):
    """Enum for processing status values."""
    PENDING = "Čaká na spracovanie"
    PROCESSING = "Spracováva sa"
    COMPLETED = "Spracované"
    ERROR = "Chyba spracovania"
    FAILED = "Neúspešné"
    CANCELLED = "Zrušené"
    
    @classmethod
    def get_default(cls):
        """Get the default status."""
        return cls.PENDING.value
    
    @classmethod
    def get_all_values(cls):
        """Get all possible status values as a list."""
        return [status.value for status in cls]

# Trieda ProcessedImageData
class ProcessedImageData(db.Model):
    __tablename__ = "processed_image_data"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=lambda: datetime.now())
    status: Mapped[str] = mapped_column(db.String(50), default=ProcessingStatus.get_default())

    technical_notes: Mapped[str] = mapped_column(db.Text, nullable=True)
    diagnostic_notes: Mapped[str] = mapped_column(db.Text, nullable=True)

    # Process Type
    #process_type_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("process_type.id"), nullable=False)
    #process_type: Mapped["ProcessTypeData"] = db.relationship("ProcessTypeData", back_populates="processed_images")
    process_type: Mapped[str] = mapped_column(db.String(20), default='process_image')

    # Cesty k obrázkom a maskám
    processed_image_path: Mapped[str] = mapped_column(db.String(255), nullable=True)
    segmentation_mask_path: Mapped[str] = mapped_column(db.String(255), nullable=True)
    bounding_boxes_path: Mapped[str] = mapped_column(db.String(255), nullable=True)

    answer: Mapped[dict] = mapped_column(db.JSON, nullable=True)

    # Vzťah k pôvodnému obrázku
    original_image_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey("original_image_data.id"), nullable=True)
    original_image: Mapped["OriginalImageData"] = relationship("OriginalImageData", back_populates="processed_images", lazy="select")
    
    def set_status(self, status: ProcessingStatus):
        """Set the processing status using the enum."""
        self.status = status.value
    
    def get_status_enum(self) -> ProcessingStatus:
        """Get the current status as an enum value."""
        for status in ProcessingStatus:
            if status.value == self.status:
                return status
        return ProcessingStatus.PENDING  # Default fallback
    
    def is_completed(self) -> bool:
        """Check if processing is completed."""
        return self.status == ProcessingStatus.COMPLETED.value
    
    def is_error(self) -> bool:
        """Check if processing has an error."""
        return self.status in [ProcessingStatus.ERROR.value, ProcessingStatus.FAILED.value]
    
    def is_pending(self) -> bool:
        """Check if processing is pending."""
        return self.status == ProcessingStatus.PENDING.value
