from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    in_stock = Column(Boolean, default=True)
    product_type = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __mapper_args__ = {
        'polymorphic_identity': 'product',
        'polymorphic_on': product_type
    }


class Flower(Product):
    __tablename__ = 'flowers'
    
    id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True)
    color = Column(String(50), nullable=False)
    season = Column(String(50), default='Всесезонный')
    
    bouquet_flowers = relationship("BouquetFlower", back_populates="flower", cascade="all, delete-orphan")
    
    __mapper_args__ = {
        'polymorphic_identity': 'FLOWER',
        'inherit_condition': id == Product.id
    }


class Bouquet(Product):
    __tablename__ = 'bouquets'
    
    id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True)
    wrapping_type = Column(String(100), nullable=False)
    flower_count = Column(Integer, default=0)
    
    bouquet_flowers = relationship("BouquetFlower", back_populates="bouquet", cascade="all, delete-orphan")
    
    __mapper_args__ = {
        'polymorphic_identity': 'BOUQUET',
        'inherit_condition': id == Product.id
    }


class BouquetFlower(Base):
    __tablename__ = 'bouquet_flowers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    bouquet_id = Column(Integer, ForeignKey('bouquets.id', ondelete='CASCADE'), nullable=False)
    flower_id = Column(Integer, ForeignKey('flowers.id', ondelete='CASCADE'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    bouquet = relationship("Bouquet", back_populates="bouquet_flowers")
    flower = relationship("Flower", back_populates="bouquet_flowers")


class Customer(Base):
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    purchases = relationship("Purchase", back_populates="customer", cascade="all, delete-orphan")


class Purchase(Base):
    __tablename__ = 'purchases'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    total_price = Column(Float)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="purchases")
    product = relationship("Product")