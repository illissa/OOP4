package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// ========== Structures ==========

type Product struct {
	ID          uint    `json:"id"`
	Name        string  `json:"name"`
	Price       float64 `json:"price"`
	InStock     bool    `json:"in_stock"`
	ProductType string  `json:"product_type"`
}

type Flower struct {
	ID      uint    `json:"id"`
	Name    string  `json:"name"`
	Color   string  `json:"color"`
	Price   float64 `json:"price"`
	Season  string  `json:"season"`
	InStock bool    `json:"in_stock"`
}

type Bouquet struct {
	ID           uint            `json:"id"`
	Name         string          `json:"name"`
	Price        float64         `json:"price"`
	WrappingType string          `json:"wrapping_type"`
	FlowerCount  int             `json:"flower_count"`
	InStock      bool            `json:"in_stock"`
	Composition  []BouquetFlower `json:"composition"`
}

type BouquetFlower struct {
	FlowerID   uint   `json:"flower_id"`
	FlowerName string `json:"flower_name"`
	Quantity   int    `json:"quantity"`
}

type Customer struct {
	ID        uint   `json:"id"`
	Name      string `json:"name"`
	Phone     string `json:"phone"`
	CreatedAt string `json:"created_at"`
}

type Purchase struct {
	ID           uint    `json:"id"`
	CustomerName string  `json:"customer_name"`
	ProductName  string  `json:"product_name"`
	Quantity     int     `json:"quantity"`
	TotalPrice   float64 `json:"total_price"`
	PurchaseDate string  `json:"purchase_date"`
}

type Statistics struct {
	FlowerCount   int     `json:"flower_count"`
	BouquetCount  int     `json:"bouquet_count"`
	CustomerCount int     `json:"customer_count"`
	AveragePrice  float64 `json:"average_price"`
	TotalSales    float64 `json:"total_sales"`
}

// ========== Cache ==========

type CacheItem struct {
	Data      interface{}
	ExpiresAt time.Time
}

var (
	cache     = make(map[string]CacheItem)
	cacheLock sync.RWMutex
	ttl       = 5 * time.Minute
)

func getCache(key string) (interface{}, bool) {
	cacheLock.RLock()
	defer cacheLock.RUnlock()
	item, found := cache[key]
	if !found || time.Now().After(item.ExpiresAt) {
		return nil, false
	}
	return item.Data, true
}

func setCache(key string, data interface{}) {
	cacheLock.Lock()
	defer cacheLock.Unlock()
	cache[key] = CacheItem{Data: data, ExpiresAt: time.Now().Add(ttl)}
}

func clearCache() {
	cacheLock.Lock()
	defer cacheLock.Unlock()
	cache = make(map[string]CacheItem)
}

// ========== Proxy ==========

const apiURL = "http://localhost:8000"

func apiGet(endpoint string, v interface{}) error {
	if cached, found := getCache(endpoint); found {
		b, _ := json.Marshal(cached)
		return json.Unmarshal(b, v)
	}
	
	fullURL := apiURL + endpoint
	fmt.Printf("[DEBUG] Запрос к Python API: %s\n", fullURL)
	
	resp, err := http.Get(fullURL)
	if err != nil {
		return fmt.Errorf("ошибка подключения: %v", err)
	}
	defer resp.Body.Close()
	
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("ошибка чтения ответа: %v", err)
	}
	
	fmt.Printf("[DEBUG] Статус ответа: %d\n", resp.StatusCode)
	
	if resp.StatusCode >= 400 {
		return fmt.Errorf("Python API ошибка %d: %s", resp.StatusCode, string(body))
	}
	
	err = json.Unmarshal(body, v)
	if err != nil {
		return fmt.Errorf("ошибка парсинга JSON: %v", err)
	}
	
	setCache(endpoint, v)
	return nil
}

func apiPost(endpoint string, payload interface{}) (map[string]interface{}, error) {
	clearCache()
	jsonData, _ := json.Marshal(payload)
	resp, err := http.Post(apiURL+endpoint, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	var result map[string]interface{}
	json.Unmarshal(body, &result)
	return result, nil
}

func apiPut(endpoint string, payload interface{}) {
	clearCache()
	jsonData, _ := json.Marshal(payload)
	req, _ := http.NewRequest("PUT", apiURL+endpoint, bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{}
	resp, _ := client.Do(req)
	defer resp.Body.Close()
}

func apiDelete(endpoint string) {
	clearCache()
	req, _ := http.NewRequest("DELETE", apiURL+endpoint, nil)
	client := &http.Client{}
	resp, _ := client.Do(req)
	defer resp.Body.Close()
}

func redirectWithMessage(c *gin.Context, urlPath string, message string) {
	c.Redirect(http.StatusFound, urlPath+"?message="+url.QueryEscape(message))
}

// ========== Main ==========

func main() {
	gin.SetMode(gin.ReleaseMode)
	r := gin.Default()
	
	r.Static("/static", "./static")
	r.LoadHTMLGlob("templates/*")
	
	// Обработка favicon
	r.GET("/favicon.ico", func(c *gin.Context) {
		c.Status(http.StatusNoContent)
	})

	// Home
	r.GET("/", func(c *gin.Context) {
		c.HTML(http.StatusOK, "index.html", nil)
	})

	// ========== FLOWERS ==========
	r.GET("/flowers", func(c *gin.Context) {
		var flowers []Flower
		
		season := c.Query("season")
		searchQuery := c.Query("search")
		currentFilter := "all"
		
		var endpoint string
		if season != "" {
			encodedSeason := url.QueryEscape(season)
			endpoint = "/api/flowers/filter/season?season=" + encodedSeason
			currentFilter = season
			fmt.Printf("[DEBUG] Фильтрация цветов по сезону: %s -> %s\n", season, encodedSeason)
		} else {
			endpoint = "/api/flowers"
			currentFilter = "all"
		}
		
		err := apiGet(endpoint, &flowers)
		if err != nil {
			fmt.Printf("[ERROR] Ошибка загрузки цветов: %v\n", err)
			c.HTML(http.StatusOK, "flowers.html", gin.H{
				"flowers":       []Flower{},
				"message":       "Ошибка загрузки данных: " + err.Error(),
				"currentFilter": currentFilter,
				"searchQuery":   searchQuery,
			})
			return
		}
		
		//по названию
		if searchQuery != "" {
			filteredFlowers := []Flower{}
			for _, flower := range flowers {
				if strings.Contains(strings.ToLower(flower.Name), strings.ToLower(searchQuery)) {
					filteredFlowers = append(filteredFlowers, flower)
				}
			}
			flowers = filteredFlowers
			currentFilter = "search_" + searchQuery
		}
		
		c.HTML(http.StatusOK, "flowers.html", gin.H{
			"flowers":       flowers,
			"message":       c.Query("message"),
			"currentFilter": currentFilter,
			"searchQuery":   searchQuery,
		})
	})

	r.GET("/flowers/add", func(c *gin.Context) {
		c.HTML(http.StatusOK, "flower-form.html", gin.H{
			"action": "/flowers/save",
			"flower": Flower{},
			"edit":   false,
		})
	})

	r.POST("/flowers/save", func(c *gin.Context) {
		name := c.PostForm("name")
		color := c.PostForm("color")
		price, _ := strconv.ParseFloat(c.PostForm("price"), 64)
		season := c.PostForm("season")
		if name == "" || color == "" {
			c.HTML(http.StatusBadRequest, "flower-form.html", gin.H{"error": "Название и цвет обязательны!", "action": "/flowers/save", "edit": false})
			return
		}
		if price < 10 {
			c.HTML(http.StatusBadRequest, "flower-form.html", gin.H{"error": "Цена не может быть меньше 10 рублей!", "action": "/flowers/save", "edit": false})
			return
		}
		apiPost("/api/flowers", map[string]interface{}{"name": name, "color": color, "price": price, "season": season})
		redirectWithMessage(c, "/flowers", "Цветок "+name+" добавлен!")
	})

	r.GET("/flowers/edit/:id", func(c *gin.Context) {
		var flower Flower
		apiGet("/api/flowers/"+c.Param("id"), &flower)
		c.HTML(http.StatusOK, "flower-form.html", gin.H{
			"action": "/flowers/update/" + c.Param("id"),
			"flower": flower,
			"edit":   true,
		})
	})

	r.POST("/flowers/update/:id", func(c *gin.Context) {
		id := c.Param("id")
		name := c.PostForm("name")
		color := c.PostForm("color")
		price, _ := strconv.ParseFloat(c.PostForm("price"), 64)
		season := c.PostForm("season")
		apiPut("/api/flowers/"+id, map[string]interface{}{"name": name, "color": color, "price": price, "season": season})
		redirectWithMessage(c, "/flowers", "Цветок "+name+" обновлён!")
	})

	r.GET("/flowers/delete/:id", func(c *gin.Context) {
		apiDelete("/api/flowers/" + c.Param("id"))
		redirectWithMessage(c, "/flowers", "Цветок удалён!")
	})

	r.GET("/flowers/water/:id", func(c *gin.Context) {
		result, _ := apiPost("/api/flowers/"+c.Param("id")+"/water", nil)
		msg := result["message"].(string)
		redirectWithMessage(c, "/flowers", msg)
	})

	r.GET("/flowers/fertilize/:id", func(c *gin.Context) {
		result, _ := apiPost("/api/flowers/"+c.Param("id")+"/fertilize", nil)
		msg := result["message"].(string)
		redirectWithMessage(c, "/flowers", msg)
	})

	r.GET("/flowers/buy/:id", func(c *gin.Context) {
		result, _ := apiPost("/api/flowers/"+c.Param("id")+"/buy", nil)
		msg := result["message"].(string)
		redirectWithMessage(c, "/flowers", msg)
	})

	r.GET("/flowers/copy/:id", func(c *gin.Context) {
		apiPost("/api/flowers/"+c.Param("id")+"/copy", nil)
		redirectWithMessage(c, "/flowers", "Цветок скопирован!")
	})

	// ========== BOUQUETS ==========
	r.GET("/bouquets", func(c *gin.Context) {
		var bouquets []Bouquet
		
		minPrice := c.Query("min_price")
		maxPrice := c.Query("max_price")
		currentFilter := "all"
		
		var endpoint string
		if minPrice != "" || maxPrice != "" {
			params := url.Values{}
			if minPrice != "" {
				params.Add("min_price", minPrice)
			}
			if maxPrice != "" {
				params.Add("max_price", maxPrice)
			}
			endpoint = "/api/bouquets/filter/price?" + params.Encode()
			if minPrice != "" && maxPrice != "" {
				currentFilter = minPrice + " - " + maxPrice
			} else if minPrice != "" {
				currentFilter = "от " + minPrice
			} else {
				currentFilter = "до " + maxPrice
			}
			fmt.Printf("[DEBUG] Фильтрация букетов по цене: %s\n", endpoint)
		} else {
			endpoint = "/api/bouquets"
			currentFilter = "all"
		}
		
		err := apiGet(endpoint, &bouquets)
		if err != nil {
			fmt.Printf("[ERROR] Ошибка загрузки букетов: %v\n", err)
			c.HTML(http.StatusOK, "bouquets.html", gin.H{
				"bouquets":      []Bouquet{},
				"message":       "Ошибка загрузки данных: " + err.Error(),
				"currentFilter": currentFilter,
				"minPrice":      minPrice,
				"maxPrice":      maxPrice,
			})
			return
		}
		
		c.HTML(http.StatusOK, "bouquets.html", gin.H{
			"bouquets":      bouquets,
			"message":       c.Query("message"),
			"currentFilter": currentFilter,
			"minPrice":      minPrice,
			"maxPrice":      maxPrice,
		})
	})

	r.GET("/bouquets/add", func(c *gin.Context) {
		c.HTML(http.StatusOK, "bouquet-form.html", gin.H{
			"action":  "/bouquets/save",
			"bouquet": Bouquet{},
			"edit":    false,
		})
	})

	r.POST("/bouquets/save", func(c *gin.Context) {
		name := c.PostForm("name")
		wrappingType := c.PostForm("wrapping_type")
		price, _ := strconv.ParseFloat(c.PostForm("price"), 64)
		if price < 100 {
			c.HTML(http.StatusBadRequest, "bouquet-form.html", gin.H{"error": "Цена букета не может быть меньше 100 рублей!", "action": "/bouquets/save", "edit": false})
			return
		}
		apiPost("/api/bouquets", map[string]interface{}{"name": name, "wrapping_type": wrappingType, "price": price})
		redirectWithMessage(c, "/bouquets", "Букет "+name+" добавлен!")
	})

	r.GET("/bouquets/edit/:id", func(c *gin.Context) {
		var bouquet Bouquet
		apiGet("/api/bouquets/"+c.Param("id"), &bouquet)
		c.HTML(http.StatusOK, "bouquet-form.html", gin.H{
			"action":  "/bouquets/update/" + c.Param("id"),
			"bouquet": bouquet,
			"edit":    true,
		})
	})

	r.POST("/bouquets/update/:id", func(c *gin.Context) {
		id := c.Param("id")
		name := c.PostForm("name")
		wrappingType := c.PostForm("wrapping_type")
		price, _ := strconv.ParseFloat(c.PostForm("price"), 64)
		apiPut("/api/bouquets/"+id, map[string]interface{}{"name": name, "wrapping_type": wrappingType, "price": price})
		redirectWithMessage(c, "/bouquets", "Букет "+name+" обновлён!")
	})

	r.POST("/bouquets/change-wrapping/:id", func(c *gin.Context) {
		id := c.Param("id")
		newWrapping := c.PostForm("wrapping_type")
		var bouquet Bouquet
		apiGet("/api/bouquets/"+id, &bouquet)
		apiPut("/api/bouquets/"+id, map[string]interface{}{"name": bouquet.Name, "wrapping_type": newWrapping, "price": bouquet.Price})
		redirectWithMessage(c, "/bouquets", "Упаковка букета "+bouquet.Name+" изменена на "+newWrapping+"!")
	})

	r.GET("/bouquets/delete/:id", func(c *gin.Context) {
		apiDelete("/api/bouquets/" + c.Param("id"))
		redirectWithMessage(c, "/bouquets", "Букет удалён!")
	})

	r.GET("/bouquets/buy/:id", func(c *gin.Context) {
		result, _ := apiPost("/api/bouquets/"+c.Param("id")+"/buy", nil)
		msg := result["message"].(string)
		redirectWithMessage(c, "/bouquets", msg)
	})

	r.GET("/bouquets/copy/:id", func(c *gin.Context) {
		apiPost("/api/bouquets/"+c.Param("id")+"/copy", nil)
		redirectWithMessage(c, "/bouquets", "Букет скопирован!")
	})

	r.POST("/bouquets/add-flower/:id", func(c *gin.Context) {
		flowerID, _ := strconv.Atoi(c.PostForm("flower_id"))
		quantity, _ := strconv.Atoi(c.PostForm("quantity"))
		if quantity < 1 {
			quantity = 1
		}
		result, _ := apiPost("/api/bouquets/"+c.Param("id")+"/add-flower", map[string]interface{}{"flower_id": flowerID, "quantity": quantity})
		redirectWithMessage(c, "/bouquets", result["message"].(string))
	})

	r.POST("/bouquets/remove-flower/:id", func(c *gin.Context) {
		flowerID, _ := strconv.Atoi(c.PostForm("flower_id"))
		quantity, _ := strconv.Atoi(c.PostForm("quantity"))
		if quantity < 1 {
			quantity = 1
		}
		result, _ := apiPost("/api/bouquets/"+c.Param("id")+"/remove-flower", map[string]interface{}{"flower_id": flowerID, "quantity": quantity})
		redirectWithMessage(c, "/bouquets", result["message"].(string))
	})

	r.GET("/bouquets/add-any-flower/:id", func(c *gin.Context) {
		result, _ := apiPost("/api/bouquets/"+c.Param("id")+"/add-any-flower", nil)
		redirectWithMessage(c, "/bouquets", result["message"].(string))
	})

	r.GET("/bouquets/remove-any-flower/:id", func(c *gin.Context) {
		result, _ := apiPost("/api/bouquets/"+c.Param("id")+"/remove-any-flower", nil)
		redirectWithMessage(c, "/bouquets", result["message"].(string))
	})

	// ========== PRODUCTS ==========
	r.GET("/products", func(c *gin.Context) {
		var products []Product
		apiGet("/api/products", &products)
		c.HTML(http.StatusOK, "products.html", gin.H{
			"products": products,
			"message":  c.Query("message"),
		})
	})

	r.GET("/products/delete/:id", func(c *gin.Context) {
		apiDelete("/api/products/" + c.Param("id"))
		redirectWithMessage(c, "/products", "Товар удалён!")
	})

	// ========== CUSTOMERS ==========
	r.GET("/customers", func(c *gin.Context) {
		var customers []Customer
		apiGet("/api/customers", &customers)
		c.HTML(http.StatusOK, "customers.html", gin.H{
			"customers": customers,
			"message":   c.Query("message"),
		})
	})

	r.GET("/customers/add", func(c *gin.Context) {
		c.HTML(http.StatusOK, "customer-form.html", nil)
	})

	r.POST("/customers/save", func(c *gin.Context) {
		name := c.PostForm("name")
		phone := c.PostForm("phone")
		if name == "" {
			c.HTML(http.StatusBadRequest, "customer-form.html", gin.H{"error": "Имя обязательно!"})
			return
		}
		apiPost("/api/customers", map[string]interface{}{"name": name, "phone": phone})
		redirectWithMessage(c, "/customers", "Клиент "+name+" добавлен!")
	})

	r.GET("/customers/delete/:id", func(c *gin.Context) {
		apiDelete("/api/customers/" + c.Param("id"))
		redirectWithMessage(c, "/customers", "Клиент удалён!")
	})

	// Страница покупки для конкретного клиента
	r.GET("/customers/buy/:id", func(c *gin.Context) {
		var customer Customer
		var products []Product
		
		err := apiGet("/api/customers/"+c.Param("id"), &customer)
		if err != nil {
			redirectWithMessage(c, "/customers", "Клиент не найден")
			return
		}
		
		apiGet("/api/products", &products)
		
		c.HTML(http.StatusOK, "customer-buy.html", gin.H{
			"Customer": customer,
			"Products": products,
			"Error":    c.Query("error"),
		})
	})

	// Обработка покупки
	r.POST("/customers/buy/:id", func(c *gin.Context) {
		customerID, _ := strconv.Atoi(c.Param("id"))
		productID, _ := strconv.Atoi(c.PostForm("product_id"))
		quantity, _ := strconv.Atoi(c.PostForm("quantity"))
		
		if quantity < 1 || quantity > 100 {
			c.Redirect(http.StatusFound, "/customers/buy/"+c.Param("id")+"?error=Количество должно быть от 1 до 100")
			return
		}
		
		result, err := apiPost("/api/purchases", map[string]interface{}{
			"customer_id": customerID,
			"product_id":  productID,
			"quantity":    quantity,
		})
		
		if err != nil {
			c.Redirect(http.StatusFound, "/customers/buy/"+c.Param("id")+"?error=Ошибка при покупке")
			return
		}
		
		redirectWithMessage(c, "/customers", "Покупка совершена! Сумма: "+fmt.Sprintf("%.2f", result["total_price"])+" руб.")
	})

	// Покупки конкретного клиента
	r.GET("/customers/:id/purchases", func(c *gin.Context) {
		customerID := c.Param("id")
		
		var customer Customer
		var purchases []Purchase
		
		apiGet("/api/customers/"+customerID, &customer)
		apiGet("/api/customers/"+customerID+"/purchases", &purchases)
		
		c.HTML(http.StatusOK, "customer-purchases.html", gin.H{
			"Customer":  customer,
			"Purchases": purchases,
			"Message":   c.Query("message"),
		})
	})

	// ========== PURCHASES ==========
	r.GET("/purchases", func(c *gin.Context) {
		var purchases []Purchase
		apiGet("/api/purchases", &purchases)
		c.HTML(http.StatusOK, "purchases.html", gin.H{"purchases": purchases})
	})

	// ========== STATISTICS ==========
	r.GET("/statistics", func(c *gin.Context) {
		var stats Statistics
		apiGet("/api/statistics", &stats)
		c.HTML(http.StatusOK, "statistics.html", gin.H{"statistics": stats})
	})

	// Start
	fmt.Println(strings.Repeat("=", 50))
	fmt.Println("Flower Shop Server")
	fmt.Println("http://localhost:3000")
	fmt.Println(strings.Repeat("=", 50))
	r.Run(":3000")
}