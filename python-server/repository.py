from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, joinedload
from models import Base, Product, Flower, Bouquet, BouquetFlower, Customer, Purchase
from typing import List, Optional
from datetime import datetime

class FlowerShopRepository:
    """ООП Репозиторий для цветочного магазина"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        print("✓ Проверка/создание таблиц выполнена")
        
        self.Session = sessionmaker(bind=self.engine)
    
    
    def _product_to_dict(self, p, session=None) -> dict:
        """Преобразует Product в словарь с учётом типа"""
        item = {
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'in_stock': p.in_stock,
            'product_type': p.product_type,
            'created_at': str(p.created_at) if p.created_at else None,
            'updated_at': str(p.updated_at) if p.updated_at else None,
        }
        if p.product_type == 'FLOWER' and session:
            flower = session.query(Flower).filter(Flower.id == p.id).first()
            if flower:
                item['color'] = flower.color
                item['season'] = flower.season
        elif p.product_type == 'BOUQUET' and session:
            bouquet = session.query(Bouquet).filter(Bouquet.id == p.id).first()
            if bouquet:
                item['wrapping_type'] = bouquet.wrapping_type
                item['flower_count'] = bouquet.flower_count or 0
                # Добавляем состав букета
                bf_list = session.query(BouquetFlower).filter(
                    BouquetFlower.bouquet_id == p.id
                ).all()
                item['composition'] = [{
                    'flower_id': bf.flower_id,
                    'flower_name': bf.flower.name if bf.flower else 'Неизвестно',
                    'quantity': bf.quantity,
                } for bf in bf_list]
        return item
    
    #Products
    
    def get_all_products(self) -> list:
        with self.Session() as session:
            products = session.query(Product).all()
            return [self._product_to_dict(p, session) for p in products]
    
    def get_product_by_id(self, product_id: int) -> Optional[dict]:
        with self.Session() as session:
            p = session.query(Product).filter(Product.id == product_id).first()
            if not p:
                return None
            return self._product_to_dict(p, session)
    
    def delete_product(self, product_id: int) -> bool:
        with self.Session() as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            if product:
                session.delete(product)
                session.commit()
                return True
            return False
    
    def buy_product(self, product_id: int) -> str:
        with self.Session() as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                return f"Ошибка: товар с ID {product_id} не найден"
            if not product.in_stock:
                return f'Товар "{product.name}" уже куплен'
            product.in_stock = False
            session.commit()
            return f'Товар "{product.name}" куплен!'
    
    def copy_product(self, product_id: int) -> dict:
        with self.Session() as session:
            p = session.query(Product).filter(Product.id == product_id).first()
            if not p:
                return None
            
            if p.product_type == 'FLOWER':
                flower = session.query(Flower).filter(Flower.id == p.id).first()
                if flower:
                    new_flower = Flower(
                        name=p.name + " (копия)",
                        color=flower.color,
                        price=p.price,
                        season=flower.season,
                        in_stock=True,
                        product_type="FLOWER"
                    )
                    session.add(new_flower)
                    session.commit()
                    return self._product_to_dict(new_flower, session)
            
            elif p.product_type == 'BOUQUET':
                bouquet = session.query(Bouquet).filter(Bouquet.id == p.id).first()
                if bouquet:
                    new_bouquet = Bouquet(
                        name=p.name + " (копия)",
                        wrapping_type=bouquet.wrapping_type,
                        price=p.price,
                        flower_count=bouquet.flower_count,
                        in_stock=True,
                        product_type="BOUQUET"
                    )
                    session.add(new_bouquet)
                    session.commit()
                    # Копируем состав букета
                    bf_list = session.query(BouquetFlower).filter(
                        BouquetFlower.bouquet_id == bouquet.id
                    ).all()
                    for bf in bf_list:
                        new_bf = BouquetFlower(
                            bouquet_id=new_bouquet.id,
                            flower_id=bf.flower_id,
                            quantity=bf.quantity
                        )
                        session.add(new_bf)
                    session.commit()
                    return self._product_to_dict(new_bouquet, session)
            return None
    
    #Flowers
    
    def get_all_flowers(self) -> list:
        with self.Session() as session:
            flowers = session.query(Flower).all()
            return [{
                'id': f.id,
                'name': f.name,
                'color': f.color,
                'price': f.price,
                'season': f.season,
                'in_stock': f.in_stock,
                'product_type': f.product_type,
                'created_at': str(f.created_at) if f.created_at else None,
            } for f in flowers]
    
    def get_flower_by_id(self, flower_id: int) -> Optional[dict]:
        with self.Session() as session:
            f = session.query(Flower).filter(Flower.id == flower_id).first()
            if not f:
                return None
            return {
                'id': f.id, 'name': f.name, 'color': f.color,
                'price': f.price, 'season': f.season,
                'in_stock': f.in_stock, 'product_type': f.product_type,
            }
    
    def create_flower(self, name: str, color: str, price: float, season: str = "Всесезонный") -> dict:
        with self.Session() as session:
            flower = Flower(
                name=name, color=color, price=price, season=season,
                in_stock=True, product_type="FLOWER"
            )
            session.add(flower)
            session.commit()
            return {'id': flower.id, 'name': flower.name, 'color': flower.color, 'price': flower.price}
    
    def update_flower(self, flower_id: int, name: str, color: str, price: float, season: str) -> Optional[dict]:
        with self.Session() as session:
            flower = session.query(Flower).filter(Flower.id == flower_id).first()
            if flower:
                flower.name = name
                flower.color = color
                flower.price = price
                flower.season = season
                session.commit()
                return {'id': flower.id, 'name': flower.name, 'color': flower.color, 'price': flower.price}
            return None
    
    def delete_flower(self, flower_id: int) -> bool:
        return self.delete_product(flower_id)
    
    def water_flower(self, flower_id: int) -> str:
        with self.Session() as session:
            flower = session.query(Flower).filter(Flower.id == flower_id).first()
            if flower:
                return f'Цветок "{flower.name}" (ID: {flower_id}) полит'
            return f"Ошибка: Цветок с ID {flower_id} не найден"
    
    def fertilize_flower(self, flower_id: int) -> str:
        with self.Session() as session:
            flower = session.query(Flower).filter(Flower.id == flower_id).first()
            if flower:
                return f'Цветок "{flower.name}" (ID: {flower_id}) удобрен'
            return f"Ошибка: Цветок с ID {flower_id} не найден"
    
    def buy_flower(self, flower_id: int) -> str:
        return self.buy_product(flower_id)
    
    def copy_flower(self, flower_id: int) -> Optional[dict]:
        return self.copy_product(flower_id)
    
    
    def get_flowers_by_season(self, season: str) -> list:
        with self.Session() as session:
            flowers = session.query(Flower).filter(Flower.season == season).all()
            return [{
                'id': f.id, 'name': f.name, 'color': f.color,
                'price': f.price, 'season': f.season, 'in_stock': f.in_stock,
            } for f in flowers]
    
    def get_flowers_in_stock(self) -> list:
        with self.Session() as session:
            flowers = session.query(Flower).filter(Flower.in_stock == True).all()
            return [{
                'id': f.id, 'name': f.name, 'color': f.color,
                'price': f.price, 'season': f.season,
            } for f in flowers]
    
    #Bouquets
    
    def get_all_bouquets(self) -> list:
        with self.Session() as session:
            bouquets = session.query(Bouquet).all()
            result = []
            for b in bouquets:
                bf_list = session.query(BouquetFlower).filter(
                    BouquetFlower.bouquet_id == b.id
                ).all()
                composition = [{
                    'flower_id': bf.flower_id,
                    'flower_name': bf.flower.name if bf.flower else 'Неизвестно',
                    'quantity': bf.quantity,
                } for bf in bf_list]
                result.append({
                    'id': b.id, 'name': b.name, 'price': b.price,
                    'wrapping_type': b.wrapping_type,
                    'flower_count': b.flower_count or 0,
                    'in_stock': b.in_stock,
                    'product_type': b.product_type,
                    'composition': composition,
                })
            return result
    
    def get_bouquet_by_id(self, bouquet_id: int) -> Optional[dict]:
        with self.Session() as session:
            b = session.query(Bouquet).filter(Bouquet.id == bouquet_id).first()
            if not b:
                return None
            bf_list = session.query(BouquetFlower).filter(
                BouquetFlower.bouquet_id == b.id
            ).all()
            return {
                'id': b.id, 'name': b.name, 'price': b.price,
                'wrapping_type': b.wrapping_type,
                'flower_count': b.flower_count or 0,
                'in_stock': b.in_stock,
                'composition': [{
                    'flower_id': bf.flower_id,
                    'flower_name': bf.flower.name if bf.flower else 'Неизвестно',
                    'quantity': bf.quantity,
                } for bf in bf_list],
            }
    
    def create_bouquet(self, name: str, wrapping_type: str, price: float) -> dict:
        with self.Session() as session:
            bouquet = Bouquet(
                name=name, wrapping_type=wrapping_type, price=price,
                flower_count=0, in_stock=True, product_type="BOUQUET"
            )
            session.add(bouquet)
            session.commit()
            return {'id': bouquet.id, 'name': bouquet.name}
    
    def update_bouquet(self, bouquet_id: int, name: str, wrapping_type: str, price: float) -> Optional[dict]:
        with self.Session() as session:
            bouquet = session.query(Bouquet).filter(Bouquet.id == bouquet_id).first()
            if bouquet:
                bouquet.name = name
                bouquet.wrapping_type = wrapping_type
                bouquet.price = price
                session.commit()
                return {'id': bouquet.id, 'name': bouquet.name}
            return None
    
    def delete_bouquet(self, bouquet_id: int) -> bool:
        return self.delete_product(bouquet_id)
    
    def buy_bouquet(self, bouquet_id: int) -> str:
        return self.buy_product(bouquet_id)
    
    def copy_bouquet(self, bouquet_id: int) -> Optional[dict]:
        return self.copy_product(bouquet_id)
    
    def add_flower_to_bouquet(self, bouquet_id: int, flower_id: int, quantity: int) -> str:
        with self.Session() as session:
            bouquet = session.query(Bouquet).filter(Bouquet.id == bouquet_id).first()
            flower = session.query(Flower).filter(Flower.id == flower_id).first()
            
            if not bouquet or not flower:
                return "Ошибка: букет или цветок не найден"
            
            existing = session.query(BouquetFlower).filter(
                BouquetFlower.bouquet_id == bouquet_id,
                BouquetFlower.flower_id == flower_id
            ).first()
            
            if existing:
                existing.quantity += quantity
            else:
                bf = BouquetFlower(bouquet_id=bouquet_id, flower_id=flower_id, quantity=quantity)
                session.add(bf)
            
            bouquet.flower_count = (bouquet.flower_count or 0) + quantity
            bouquet.price = (bouquet.price or 0) + (flower.price * quantity)
            session.commit()
            return f'Добавлен цветок "{flower.name}" ({quantity} шт.) в букет "{bouquet.name}"'
    
    def remove_flower_from_bouquet(self, bouquet_id: int, flower_id: int, quantity: int) -> str:
        with self.Session() as session:
            bouquet = session.query(Bouquet).filter(Bouquet.id == bouquet_id).first()
            flower = session.query(Flower).filter(Flower.id == flower_id).first()
            
            if not bouquet or not flower:
                return "Ошибка: букет или цветок не найден"
            
            existing = session.query(BouquetFlower).filter(
                BouquetFlower.bouquet_id == bouquet_id,
                BouquetFlower.flower_id == flower_id
            ).first()
            
            if not existing:
                return f'Ошибка: цветок "{flower.name}" не найден в букете'
            
            if existing.quantity <= quantity:
                session.delete(existing)
                bouquet.flower_count -= existing.quantity
                bouquet.price -= flower.price * existing.quantity
                session.commit()
                return f'Цветок "{flower.name}" полностью удалён из букета "{bouquet.name}"'
            else:
                existing.quantity -= quantity
                bouquet.flower_count -= quantity
                bouquet.price -= flower.price * quantity
                session.commit()
                return f'Убрано {quantity} шт. "{flower.name}" из букета "{bouquet.name}"'
    
    def add_any_flower_to_bouquet(self, bouquet_id: int) -> str:
        with self.Session() as session:
            bouquet = session.query(Bouquet).filter(Bouquet.id == bouquet_id).first()
            if not bouquet:
                return "Ошибка: букет не найден"
            bouquet.flower_count = (bouquet.flower_count or 0) + 1
            bouquet.price = (bouquet.price or 0) + 100
            session.commit()
            return f'Добавлен цветок в букет "{bouquet.name}". Теперь: {bouquet.flower_count} цветов, цена: {bouquet.price:.2f} руб.'
    
    def remove_any_flower_from_bouquet(self, bouquet_id: int) -> str:
        with self.Session() as session:
            bouquet = session.query(Bouquet).filter(Bouquet.id == bouquet_id).first()
            if not bouquet:
                return "Ошибка: букет не найден"
            if bouquet.flower_count <= 0:
                return "Ошибка: в букете нет цветов"
            bouquet.flower_count -= 1
            bouquet.price = max(0, (bouquet.price or 0) - 100)
            session.commit()
            return f'Цветок убран из букета "{bouquet.name}". Теперь: {bouquet.flower_count} цветов, цена: {bouquet.price:.2f} руб.'
    
    # Фильтрация букетов по цене
    def get_bouquets_by_price(self, min_price: Optional[float] = None, max_price: Optional[float] = None) -> list:
        """Фильтрация букетов по цене"""
        with self.Session() as session:
            query = session.query(Bouquet)
            if min_price is not None:
                query = query.filter(Bouquet.price >= min_price)
            if max_price is not None:
                query = query.filter(Bouquet.price <= max_price)
            bouquets = query.all()
            result = []
            for b in bouquets:
                bf_list = session.query(BouquetFlower).filter(
                    BouquetFlower.bouquet_id == b.id
                ).all()
                composition = [{
                    'flower_id': bf.flower_id,
                    'flower_name': bf.flower.name if bf.flower else 'Неизвестно',
                    'quantity': bf.quantity,
                } for bf in bf_list]
                result.append({
                    'id': b.id, 'name': b.name, 'price': b.price,
                    'wrapping_type': b.wrapping_type,
                    'flower_count': b.flower_count or 0,
                    'in_stock': b.in_stock,
                    'product_type': b.product_type,
                    'composition': composition,
                })
            return result
    
    #Customers
    
    def get_all_customers(self) -> list:
        with self.Session() as session:
            customers = session.query(Customer).all()
            return [{
                'id': c.id, 'name': c.name, 'phone': c.phone,
                'created_at': str(c.created_at) if c.created_at else None,
            } for c in customers]
    
    def get_customer_by_id(self, customer_id: int) -> Optional[dict]:
        with self.Session() as session:
            c = session.query(Customer).filter(Customer.id == customer_id).first()
            if not c:
                return None
            return {'id': c.id, 'name': c.name, 'phone': c.phone}
    
    def create_customer(self, name: str, phone: str = "") -> dict:
        with self.Session() as session:
            customer = Customer(name=name, phone=phone)
            session.add(customer)
            session.commit()
            return {'id': customer.id, 'name': customer.name}
    
    def delete_customer(self, customer_id: int) -> bool:
        with self.Session() as session:
            customer = session.query(Customer).filter(Customer.id == customer_id).first()
            if customer:
                session.delete(customer)
                session.commit()
                return True
            return False
    
    #Purchases
    
    def get_all_purchases(self) -> list:
        with self.Session() as session:
            purchases = session.query(Purchase).options(
                joinedload(Purchase.customer),
                joinedload(Purchase.product)
            ).all()
            return [{
                'id': p.id, 'customer_id': p.customer_id,
                'product_id': p.product_id, 'quantity': p.quantity,
                'total_price': p.total_price,
                'purchase_date': str(p.purchase_date) if p.purchase_date else None,
                'customer_name': p.customer.name if p.customer else 'Неизвестно',
                'product_name': p.product.name if p.product else 'Неизвестно',
            } for p in purchases]
    
    def get_customer_purchases(self, customer_id: int) -> list:
        with self.Session() as session:
            purchases = session.query(Purchase).options(
                joinedload(Purchase.product)
            ).filter(Purchase.customer_id == customer_id).all()
            return [{
                'id': p.id, 'product_name': p.product.name if p.product else 'Неизвестно',
                'quantity': p.quantity, 'total_price': p.total_price,
                'purchase_date': str(p.purchase_date) if p.purchase_date else None,
            } for p in purchases]
    
    def create_purchase(self, customer_id: int, product_id: int, quantity: int = 1) -> dict:
        with self.Session() as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise ValueError(f"Товар с ID {product_id} не найден")
            
            purchase = Purchase(
                customer_id=customer_id, product_id=product_id,
                quantity=quantity, total_price=product.price * quantity
            )
            session.add(purchase)
            session.commit()
            return {
                'id': purchase.id, 'total_price': purchase.total_price,
                'product_name': product.name,
            }
    
    #Statistics 
    
    def get_statistics(self) -> dict:
        with self.Session() as session:
            flower_count = session.query(func.count(Flower.id)).scalar() or 0
            bouquet_count = session.query(func.count(Bouquet.id)).scalar() or 0
            customer_count = session.query(func.count(Customer.id)).scalar() or 0
            avg_price = session.query(func.avg(Product.price)).scalar()
            total_sales = session.query(func.sum(Purchase.total_price)).scalar() or 0
            
            return {
                'flower_count': flower_count,
                'bouquet_count': bouquet_count,
                'customer_count': customer_count,
                'average_price': round(float(avg_price), 2) if avg_price else 0,
                'total_sales': round(float(total_sales), 2)
            }