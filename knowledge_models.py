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
    related_product_group = Column(Text)
    approval_status = Column(String, default="Approved")
    extracted_text = Column(Text)
    parser_raw_json = Column(Text)
    parser_provider = Column(String)
    parser_confidence = Column(String)
    parser_warnings = Column(Text)
    metadata_review_status = Column(String, default="needs_review")
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
    approval_status = Column(String, default="Approved")
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
    approval_status = Column(String, default="Approved")
    created_by = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeIntelligence(Base):
    __tablename__ = "knowledge_intelligence"

    id = Column(Integer, primary_key=True)
    intelligence_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    entity_name = Column(String)
    country = Column(String)
    lane = Column(String)
    commodity = Column(String)
    hs_code = Column(String)
    summary = Column(Text)
    details = Column(Text)
    source = Column(Text)
    source_type = Column(String)
    source_id = Column(Integer)
    confidence = Column(String, default="Medium")
    tags = Column(Text)
    status = Column(String, default="Active")
    approval_status = Column(String, default="Approved")
    created_by = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ComplianceProductGroup(Base):
    __tablename__ = "compliance_product_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True)
    description = Column(Text)
    managing_authority = Column(String)
    status = Column(String, default="Active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True)
    product_group_id = Column(Integer, ForeignKey("compliance_product_groups.id"))
    rule_title = Column(String, nullable=False)
    rule_type = Column(String)
    legal_document_id = Column(Integer, ForeignKey("knowledge_documents.id"))
    article_no = Column(String)
    clause_no = Column(String)
    appendix_no = Column(String)
    table_no = Column(String)
    content = Column(Text)
    required_documents = Column(Text)
    managing_authority = Column(String)
    effective_date = Column(String)
    approval_status = Column(String, default="pending_review")
    confidence_score = Column(String)
    source_chunk_id = Column(Integer, ForeignKey("knowledge_chunks.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ComplianceKeyword(Base):
    __tablename__ = "compliance_keywords"
    __table_args__ = (UniqueConstraint("product_group_id", "keyword"),)

    id = Column(Integer, primary_key=True)
    product_group_id = Column(Integer, ForeignKey("compliance_product_groups.id"))
    keyword = Column(String, nullable=False)
    keyword_type = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class ComplianceNote(Base):
    __tablename__ = "compliance_notes"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    topic = Column(String)
    product_group_id = Column(Integer, ForeignKey("compliance_product_groups.id"))
    summary = Column(Text)
    interpretation = Column(Text)
    operational_guidance = Column(Text)
    risk_notes = Column(Text)
    related_documents = Column(Text)
    related_sops = Column(Text)
    related_cases = Column(Text)
    approval_status = Column(String, default="Pending")
    created_by = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
