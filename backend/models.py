from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text
from database import Base
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True)
    password = Column(String(255))
    role = Column(String(20), nullable=False, default="user", server_default="user")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

class DataFile(Base):
    __tablename__ = "data_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stored_name = Column(String(255), unique=True, nullable=False)
    original_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ImageFile(Base):
    __tablename__ = "image_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stored_name = Column(String(255), unique=True, nullable=False)
    original_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    mime_type = Column(String(100), nullable=False, default="image/png")
    source_image_id = Column(Integer, ForeignKey("image_files.id"), nullable=True)
    operation_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ImageProcessingHistory(Base):
    __tablename__ = "image_processing_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_image_id = Column(Integer, ForeignKey("image_files.id"), nullable=False)
    result_image_id = Column(Integer, ForeignKey("image_files.id"), nullable=True)
    action_type = Column(String(50), nullable=False)
    operation_summary = Column(Text, nullable=False)
    result_payload = Column(Text, nullable=True)
    exported = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("data_files.id"), nullable=False)
    column_name = Column(String(100), nullable=False)
    chart_type = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CleaningHistory(Base):
    __tablename__ = "cleaning_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_file_id = Column(Integer, ForeignKey("data_files.id"), nullable=False)
    result_file_id = Column(Integer, ForeignKey("data_files.id"), nullable=False)
    operation_summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalysisPlan(Base):
    __tablename__ = "analysis_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("data_files.id"), nullable=False)
    name = Column(String(100), nullable=False)
    plan_config = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
