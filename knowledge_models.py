from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    document_no = Column(String)
    document_type = Column(String)
    issuing_authority = Column(String)
    issue_date = Column(String)
    effective_date = Column(String)
    expiry_date = Column(String)
    status = Column(String)
    category = Column(String)
    source_url = Column(String)
    file_path = Column(String)
    summary = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    chunks = relationship("KnowledgeChunk", back_populates="document")
    tags = relationship("KnowledgeDocumentTag", back_populates="document")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"))
    article_no = Column(String)
    clause_no = Column(String)
    heading = Column(String)
    content = Column(Text)
    keywords = Column(Text)
    embedding = Column(Text)
    status = Column(String, default="Approved")
    created_at = Column(DateTime, server_default=func.now())

    document = relationship("KnowledgeDocument", back_populates="chunks")


class KnowledgeCase(Base):
    __tablename__ = "knowledge_cases"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    customer = Column(String)
    commodity = Column(String)
    hs_code = Column(String)
    country = Column(String)
    problem = Column(Text)
    solution = Column(Text)
    legal_basis = Column(Text)
    risk_notes = Column(Text)
    attachments = Column(Text)
    created_by = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeTag(Base):
    __tablename__ = "knowledge_tags"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)


class KnowledgeDocumentTag(Base):
    __tablename__ = "knowledge_document_tags"
    __table_args__ = (UniqueConstraint("document_id", "tag_id"),)

    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("knowledge_tags.id"), primary_key=True)

    document = relationship("KnowledgeDocument", back_populates="tags")
    tag = relationship("KnowledgeTag")


class KnowledgeSOP(Base):
    __tablename__ = "knowledge_sops"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    purpose = Column(Text)
    procedure_steps = Column(Text)
    checklist = Column(Text)
    related_documents = Column(Text)
    related_cases = Column(Text)
    category = Column(String)
    status = Column(String, default="Active")
    created_by = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
