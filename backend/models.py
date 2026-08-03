from sqlalchemy import (create_engine,Column,Integer,String,Text,JSON)
from sqlalchemy.orm import (declarative_base,sessionmaker)

DATABASE_URL = "postgresql://postgres:Audrey@localhost/rag2_db"
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base = declarative_base()

class Chunk(Base):

    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(String, unique=True, nullable=False)
    source_file = Column(String, nullable=False)
    page_number = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    title = Column(Text,nullable=True)
    metadata_json = Column(JSON,nullable=True)
    image_path = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)