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

# new models -- for promotions data -- 30/07/25

from django.db import models

class CustomerPromotionJune(models.Model):
    title = models.CharField(max_length=255)
    itemid = models.CharField(max_length=255)
    productid = models.BigIntegerField()
    varientid = models.BigIntegerField()
    price = models.CharField(max_length=50, null=True, blank=True)

    clicks = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conv_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conv_value_per_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impr = models.IntegerField(default=0)
    ctr = models.CharField(max_length=20, null=True, blank=True)
    avg_cpc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conversions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost_conv = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conv_value_click = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    value_conv = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conv_rate = models.CharField(max_length=20, null=True, blank=True)

    all_conv = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    all_conv_value_click = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    all_conv_value_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost_all_conv = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    value_all_conv = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    all_conv_rate = models.CharField(max_length=20, null=True, blank=True)
    all_conv_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    units_sold = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_order_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    orders = models.IntegerField(default=0)
    avg_basket_size = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost_of_goods_sold = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    lead_units_sold = models.IntegerField(default=0)
    cross_sell_units_sold = models.IntegerField(default=0)
    lead_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cross_sell_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cross_device_conv = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cross_device_conv_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    category_1st_level = models.CharField(max_length=255, null=True, blank=True)
    category_5th_level = models.CharField(max_length=255, null=True, blank=True)
    category_2nd_level = models.CharField(max_length=255, null=True, blank=True)
    category_3rd_level = models.CharField(max_length=255, null=True, blank=True)
    category_4th_level = models.CharField(max_length=255, null=True, blank=True)
    product_type_1st_level = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "customer_promotion_june"

    def __str__(self):
        return f"{self.title} ({self.itemid})"
    
    from django.db import models

class CustomerPromotion_May(models.Model):
    title = models.CharField(max_length=255)
    item_id = models.CharField(max_length=255)
    product_id = models.BigIntegerField()
    variant_id = models.BigIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    clicks = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conv_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conv_value_per_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    impressions = models.IntegerField(default=0)
    ctr = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_cpc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conversions = models.IntegerField(default=0)
    cost_per_conv = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conv_value_per_click = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    value_per_conv = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conv_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    all_conv = models.IntegerField(default=0)
    all_conv_value_per_click = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    all_conv_value_per_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_per_all_conv = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    value_per_all_conv = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    all_conv_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    all_conv_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    units_sold = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    avg_order_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    orders = models.IntegerField(default=0)
    avg_basket_size = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_of_goods_sold = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    lead_units_sold = models.IntegerField(default=0)
    cross_sell_units_sold = models.IntegerField(default=0)
    lead_revenue = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cross_sell_revenue = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cross_device_conv = models.IntegerField(default=0)
    cross_device_conv_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    category_1st_level = models.CharField(max_length=255, null=True, blank=True)
    category_5th_level = models.CharField(max_length=255, null=True, blank=True)
    category_2nd_level = models.CharField(max_length=255, null=True, blank=True)
    category_3rd_level = models.CharField(max_length=255, null=True, blank=True)
    category_4th_level = models.CharField(max_length=255, null=True, blank=True)
    product_type_1st_level = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'customer_promotion_may'

    def __str__(self):
        return f"{self.title} - {self.item_id}"
    

    from django.db import models

class CustomerPromotion_April(models.Model):
    title = models.CharField(max_length=255)
    item_id = models.CharField(max_length=255)
    product_id = models.BigIntegerField()
    variant_id = models.BigIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    clicks = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conv_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conv_value_per_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    impressions = models.IntegerField(default=0)
    ctr = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_cpc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conversions = models.IntegerField(default=0)
    cost_per_conv = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conv_value_per_click = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    value_per_conv = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    conv_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    all_conv = models.IntegerField(default=0)
    all_conv_value_per_click = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    all_conv_value_per_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_per_all_conv = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    value_per_all_conv = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    all_conv_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    all_conv_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    units_sold = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    avg_order_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    orders = models.IntegerField(default=0)
    avg_basket_size = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_of_goods_sold = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    lead_units_sold = models.IntegerField(default=0)
    cross_sell_units_sold = models.IntegerField(default=0)
    lead_revenue = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cross_sell_revenue = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cross_device_conv = models.IntegerField(default=0)
    cross_device_conv_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    category_1st_level = models.CharField(max_length=255, null=True, blank=True)
    category_5th_level = models.CharField(max_length=255, null=True, blank=True)
    category_2nd_level = models.CharField(max_length=255, null=True, blank=True)
    category_3rd_level = models.CharField(max_length=255, null=True, blank=True)
    category_4th_level = models.CharField(max_length=255, null=True, blank=True)
    product_type_1st_level = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'customer_promotion_april'

    def __str__(self):
        return f"{self.title} - {self.item_id}"


