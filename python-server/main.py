from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import uvicorn
from repository import FlowerShopRepository

app = FastAPI(title="Flower Shop API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "postgresql+psycopg://postgres:12345678@localhost:5432/flower_shop"
repo = FlowerShopRepository(DATABASE_URL)

# ========== Pydantic модели ==========

class FlowerCreate(BaseModel):
    name: str
    color: str
    price: float
    season: Optional[str] = "Всесезонный"

class FlowerUpdate(BaseModel):
    name: str
    color: str
    price: float
    season: Optional[str] = "Всесезонный"

class BouquetCreate(BaseModel):
    name: str
    wrapping_type: str
    price: float

class BouquetUpdate(BaseModel):
    name: str
    wrapping_type: str
    price: float

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = ""

class PurchaseCreate(BaseModel):
    customer_id: int
    product_id: int
    quantity: int = 1

class AddFlowerToBouquet(BaseModel):
    flower_id: int
    quantity: int = 1

class RemoveFlowerFromBouquet(BaseModel):
    flower_id: int
    quantity: int = 1

# ========== Root ==========
@app.get("/")
def root():
    return {"message": "Flower Shop API v2.0", "status": "running"}

# ========== Favicon ==========
@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

# ========== Products ==========
@app.get("/api/products")
def get_products():
    return repo.get_all_products()

@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    product = repo.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int):
    if repo.delete_product(product_id):
        return {"message": "Товар удалён"}
    raise HTTPException(status_code=404, detail="Товар не найден")

@app.post("/api/products/{product_id}/buy")
def buy_product(product_id: int):
    result = repo.buy_product(product_id)
    return {"message": result}

@app.post("/api/products/{product_id}/copy")
def copy_product(product_id: int):
    product = repo.copy_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product

# ========== Flowers ==========
@app.get("/api/flowers")
def get_flowers():
    return repo.get_all_flowers()

@app.get("/api/flowers/{flower_id}")
def get_flower(flower_id: int):
    flower = repo.get_flower_by_id(flower_id)
    if not flower:
        raise HTTPException(status_code=404, detail="Цветок не найден")
    return flower

@app.post("/api/flowers")
def create_flower(data: FlowerCreate):
    return repo.create_flower(data.name, data.color, data.price, data.season)

@app.put("/api/flowers/{flower_id}")
def update_flower(flower_id: int, data: FlowerUpdate):
    flower = repo.update_flower(flower_id, data.name, data.color, data.price, data.season)
    if not flower:
        raise HTTPException(status_code=404, detail="Цветок не найден")
    return flower

@app.delete("/api/flowers/{flower_id}")
def delete_flower(flower_id: int):
    if repo.delete_flower(flower_id):
        return {"message": "Цветок удалён"}
    raise HTTPException(status_code=404, detail="Цветок не найден")

@app.post("/api/flowers/{flower_id}/water")
def water_flower(flower_id: int):
    return {"message": repo.water_flower(flower_id)}

@app.post("/api/flowers/{flower_id}/fertilize")
def fertilize_flower(flower_id: int):
    return {"message": repo.fertilize_flower(flower_id)}

@app.post("/api/flowers/{flower_id}/buy")
def buy_flower(flower_id: int):
    return {"message": repo.buy_flower(flower_id)}

@app.post("/api/flowers/{flower_id}/copy")
def copy_flower(flower_id: int):
    flower = repo.copy_flower(flower_id)
    if not flower:
        raise HTTPException(status_code=404, detail="Цветок не найден")
    return flower

# ========== Фильтрация цветов по сезону ==========
@app.get("/api/flowers/filter/season")
def filter_flowers_by_season(season: str = Query(..., description="Сезон: Весна, Лето, Осень, Зима, Всесезонный")):
    print(f"Фильтрация цветов по сезону: {season}")
    result = repo.get_flowers_by_season(season)
    print(f"Найдено цветов: {len(result)}")
    return result

# ========== Фильтрация букетов по цене ==========
@app.get("/api/bouquets/filter/price")
def filter_bouquets_by_price(
    min_price: Optional[float] = Query(None, description="Минимальная цена"),
    max_price: Optional[float] = Query(None, description="Максимальная цена")
):
    print(f"Фильтрация букетов по цене: от {min_price} до {max_price}")
    result = repo.get_bouquets_by_price(min_price, max_price)
    print(f"Найдено букетов: {len(result)}")
    return result

# ========== Bouquets ==========
@app.get("/api/bouquets")
def get_bouquets():
    return repo.get_all_bouquets()

@app.get("/api/bouquets/{bouquet_id}")
def get_bouquet(bouquet_id: int):
    bouquet = repo.get_bouquet_by_id(bouquet_id)
    if not bouquet:
        raise HTTPException(status_code=404, detail="Букет не найден")
    return bouquet

@app.post("/api/bouquets")
def create_bouquet(data: BouquetCreate):
    return repo.create_bouquet(data.name, data.wrapping_type, data.price)

@app.put("/api/bouquets/{bouquet_id}")
def update_bouquet(bouquet_id: int, data: BouquetUpdate):
    bouquet = repo.update_bouquet(bouquet_id, data.name, data.wrapping_type, data.price)
    if not bouquet:
        raise HTTPException(status_code=404, detail="Букет не найден")
    return bouquet

@app.delete("/api/bouquets/{bouquet_id}")
def delete_bouquet(bouquet_id: int):
    if repo.delete_bouquet(bouquet_id):
        return {"message": "Букет удалён"}
    raise HTTPException(status_code=404, detail="Букет не найден")

@app.post("/api/bouquets/{bouquet_id}/buy")
def buy_bouquet(bouquet_id: int):
    return {"message": repo.buy_bouquet(bouquet_id)}

@app.post("/api/bouquets/{bouquet_id}/copy")
def copy_bouquet(bouquet_id: int):
    bouquet = repo.copy_bouquet(bouquet_id)
    if not bouquet:
        raise HTTPException(status_code=404, detail="Букет не найден")
    return bouquet

@app.post("/api/bouquets/{bouquet_id}/add-flower")
def add_flower(bouquet_id: int, data: AddFlowerToBouquet):
    return {"message": repo.add_flower_to_bouquet(bouquet_id, data.flower_id, data.quantity)}

@app.post("/api/bouquets/{bouquet_id}/remove-flower")
def remove_flower(bouquet_id: int, data: RemoveFlowerFromBouquet):
    return {"message": repo.remove_flower_from_bouquet(bouquet_id, data.flower_id, data.quantity)}

@app.post("/api/bouquets/{bouquet_id}/add-any-flower")
def add_any_flower(bouquet_id: int):
    return {"message": repo.add_any_flower_to_bouquet(bouquet_id)}

@app.post("/api/bouquets/{bouquet_id}/remove-any-flower")
def remove_any_flower(bouquet_id: int):
    return {"message": repo.remove_any_flower_from_bouquet(bouquet_id)}

# ========== Customers ==========
@app.get("/api/customers")
def get_customers():
    return repo.get_all_customers()

@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: int):
    customer = repo.get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return customer

@app.post("/api/customers")
def create_customer(data: CustomerCreate):
    return repo.create_customer(data.name, data.phone)

@app.delete("/api/customers/{customer_id}")
def delete_customer(customer_id: int):
    if repo.delete_customer(customer_id):
        return {"message": "Клиент удалён"}
    raise HTTPException(status_code=404, detail="Клиент не найден")

# ========== Purchases ==========
@app.get("/api/purchases")
def get_purchases():
    return repo.get_all_purchases()

@app.get("/api/customers/{customer_id}/purchases")
def get_customer_purchases(customer_id: int):
    return repo.get_customer_purchases(customer_id)

@app.post("/api/purchases")
def create_purchase(data: PurchaseCreate):
    try:
        return repo.create_purchase(data.customer_id, data.product_id, data.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ========== Statistics ==========
@app.get("/api/statistics")
def get_statistics():
    return repo.get_statistics()

if __name__ == "__main__":
    print("=" * 50)
    print("Flower Shop API Server v2.0")
    print("=" * 50)
    print("Server: http://localhost:8000")
    print("Documentation: http://localhost:8000/docs")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")