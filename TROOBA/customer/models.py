from django.db import models

# --- Lookup / Metadata Tables ---

class Customer(models.Model):
    shopify_id = models.BigIntegerField(unique=True)
    email = models.EmailField(null=True, blank=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    city = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    tags = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name or self.email

class Location(models.Model):
    shopify_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

class Event(models.Model):
    name = models.CharField(max_length=100)  # e.g., "Diwali", "Black Friday"
    start_date = models.DateField()
    end_date = models.DateField()
    region = models.CharField(max_length=100, null=True, blank=True)  # Optional

    def __str__(self):
        return f"{self.name} ({self.start_date})"

# --- Orders + Context ---

class Order(models.Model):
    shopify_id = models.BigIntegerField(unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True)
    order_date = models.DateTimeField()

    # AI Context Fields
    day_of_week = models.CharField(max_length=10)   # Monday, Tuesday, etc.
    season = models.CharField(max_length=20)        # Summer, Monsoon, etc.
    time_slot = models.CharField(max_length=20)     # Morning, Afternoon, Evening
    total_price = models.FloatField()

    def __str__(self):
        return f"Order {self.shopify_id}"

class Product(models.Model):
    shopify_id = models.BigIntegerField(unique=True)
    title = models.CharField(max_length=255)
    product_type = models.CharField(max_length=255, null=True, blank=True)
    vendor = models.CharField(max_length=255, null=True, blank=True)
    tags = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title

class ProductVariant(models.Model):
    shopify_id = models.BigIntegerField(unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, null=True, blank=True)
    price = models.FloatField()

    def __str__(self):
        return f"{self.product.title} - {self.title}"

class OrderLineItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    price = models.FloatField()
    product_type = models.CharField(max_length=255, null=True, blank=True)  # For redundancy

# --- Sales Prediction ---

class SalesPrediction(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    
    # AI Features
    season = models.CharField(max_length=20)
    day_of_week = models.CharField(max_length=10)
    time_slot = models.CharField(max_length=20)
    
    predicted_sales = models.FloatField()
    actual_sales = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.product.title} on {self.date} @ {self.location.name}"
    
class Prompt(models.Model):
    prompt=models.TextField(max_length=100000)
    type=models.TextField(max_length=100,default="Header")