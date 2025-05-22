from sqlalchemy import Column, Integer, String, Float, DateTime
from app.infrastructure.database.db import Base

class TransactionDB(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String)
    amount = Column(Float)
    date = Column(DateTime)
    source = Column(String)
    email_id = Column(String, unique=True)
