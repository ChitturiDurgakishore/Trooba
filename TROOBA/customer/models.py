from django.db import models
# Note: ArrayField is specific to PostgreSQL. Since you're using MySQL,
# we'll keep `tags` as a TextField.

# 1. Location Table
class Location(models.Model):
    shopify_location_id = models.CharField(max_length=255, unique=True, null=True, blank=True,
                                           help_text="Shopify's ID for a physical store location, if applicable.")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    region = models.CharField(max_length=100, null=True, blank=True,
                              help_text="Broader geographical region (e.g., North, South, East, West).")
    cultural_traits = models.TextField(null=True, blank=True,
                                       help_text="JSON or text describing local preferences, traditions, festivals, e.g., 'High demand for gold during Diwali'.")
    population_density = models.IntegerField(null=True, blank=True,
                                             help_text="Population density of the area.")
    average_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                         help_text="Average income of residents in this location.")

    def __str__(self):
        return f"{self.city}, {self.state}, {self.country}"

# 2. CustomerProfile Table
class CustomerProfile(models.Model):
    shopify_customer_id = models.CharField(max_length=255, unique=True, null=True, blank=True,
                                           help_text="Shopify's unique ID for this customer.")
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True,
                              help_text="Customer's email address (can be null for guest checkouts).")
    phone = models.CharField(max_length=20, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True,
                                 help_text="Inferred location of the customer based on shipping/billing address.")
    gender = models.CharField(max_length=20, null=True, blank=True)
    age_range = models.CharField(max_length=20, null=True, blank=True,
                                 help_text="e.g., '18-24', '25-34', '35-44'.")
    purchase_style = models.TextField(null=True, blank=True,
                                      help_text="Describes customer's buying habits, e.g., 'budget-conscious', 'luxury-seeker', 'gift-buyer', 'impulse'.")
    accepts_marketing = models.BooleanField(default=False,
                                            help_text="Does the customer accept marketing emails?")
    total_orders_count = models.PositiveIntegerField(default=0,
                                                     help_text="Total number of orders placed by this customer.")
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                      help_text="Total amount spent by this customer.")
    created_at = models.DateTimeField(null=True, blank=True,
                                      help_text="Timestamp when the customer record was created in Shopify.")
    updated_at = models.DateTimeField(null=True, blank=True,
                                      help_text="Timestamp when the customer record was last updated in Shopify.")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})" if self.email else f"Customer ID: {self.shopify_customer_id or 'N/A'}"

# 3. ProductDetail Table (MODIFIED - uses existing table and renames ID)
class ProductDetail(models.Model):
    # Assuming your existing table has an auto-incrementing 'id' column.
    # We will map Shopify Product ID to a new field or rename the existing PK.
    # If your original `id` was BigAutoField, it's safer to add shopify_product_id as a new unique field.
    # If you want to rename the existing primary key column, you'll need a custom migration.
    # For simplicity, let's assume `id` remains the primary key, and `shopify_product_id` is a unique field.
    id = models.BigAutoField(primary_key=True) # Keep your existing auto-incrementing ID
    shopify_product_id = models.CharField(max_length=255, unique=True, null=True, blank=True,
                                          help_text="Shopify's unique ID for the product.")
    title = models.CharField(max_length=255,
                             help_text="Main title of the product (e.g., 'Classic Diamond Ring').")
    handle = models.CharField(max_length=255, null=True, blank=True,
                              help_text="URL slug for the product on Shopify.")
    vendor = models.CharField(max_length=100,
                              help_text="Vendor or brand of the product.")
    product_type = models.CharField(max_length=50,
                                    help_text="General category like 'Ring', 'Necklace', 'Earrings'.")
    status = models.CharField(max_length=50,
                              help_text="Product status: 'active', 'draft', 'archived'.")
    tags = models.TextField(null=True, blank=True,
                            help_text="Comma-separated string of product tags from Shopify.")
    created_at = models.DateTimeField(
        help_text="Timestamp when the product was created in Shopify.")
    updated_at = models.DateTimeField(
        help_text="Timestamp when the product was last updated in Shopify.")
    published_at = models.DateTimeField(null=True, blank=True,
                                        help_text="Timestamp when the product was published to sales channels.")

    # Removed: metal_type, karat, weight_grams, stone_type, subcategory, sku, price, inventory_quantity
    # These will now be in ProductVariant.

    def __str__(self):
        return self.title

# 4. ProductImage Table
class ProductImage(models.Model):
    shopify_image_id = models.CharField(max_length=255, unique=True,
                                        help_text="Shopify's unique ID for the image.")
    product = models.ForeignKey(ProductDetail, on_delete=models.CASCADE, related_name='images',
                                help_text="The product this image belongs to.")
    src = models.URLField(max_length=500,
                          help_text="URL of the product image.")
    alt = models.CharField(max_length=255, null=True, blank=True,
                           help_text="Alt text for the image.")
    position = models.PositiveIntegerField(null=True, blank=True,
                                           help_text="Order of the image in Shopify's product gallery.")
    variant_ids = models.TextField(null=True, blank=True,
                                   help_text="JSON string or comma-separated list of Shopify variant IDs this image represents.")

    def __str__(self):
        return f"Image for {self.product.title}"

# 5. ProductOption Table
class ProductOption(models.Model):
    product = models.ForeignKey(ProductDetail, on_delete=models.CASCADE, related_name='options',
                                help_text="The product this option belongs to.")
    shopify_option_id = models.CharField(max_length=255, unique=True, null=True, blank=True,
                                        help_text="Shopify's ID for this product option.")
    name = models.CharField(max_length=100,
                            help_text="Name of the option (e.g., 'Metal Type', 'Karat', 'Size').")
    position = models.PositiveIntegerField(
        help_text="Order of the option as defined in Shopify.")

    def __str__(self):
        return f"{self.product.title} - {self.name}"

# 6. ProductOptionValue Table
class ProductOptionValue(models.Model):
    option = models.ForeignKey(ProductOption, on_delete=models.CASCADE, related_name='values',
                               help_text="The product option this value belongs to.")
    value = models.CharField(max_length=100,
                             help_text="Specific value of the option (e.g., 'Gold', 'Silver', '14K', '18K', '7', '8').")
    position = models.PositiveIntegerField(
        help_text="Order of the value within its option.")

    def __str__(self):
        return f"{self.option.name}: {self.value}"

# 7. ProductVariant Table (New, will be created)
class ProductVariant(models.Model):
    # This will be a new table. Its primary key should be the Shopify Variant ID.
    shopify_variant_id = models.CharField(max_length=255, unique=True, primary_key=True,
                                          help_text="Shopify's unique ID for this product variant.")
    product = models.ForeignKey(ProductDetail, on_delete=models.CASCADE, related_name='variants',
                                help_text="The parent product this variant belongs to.")
    title = models.CharField(max_length=255,
                             help_text="Full title of the variant (e.g., 'Gold / 14K / Size 7').")
    sku = models.CharField(max_length=100, null=True, blank=True, unique=True,
                          help_text="Stock Keeping Unit for this specific variant.")
    price = models.DecimalField(max_digits=12, decimal_places=2,
                                help_text="Selling price of this variant.")
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                     help_text="Cost of goods for this variant (CRUCIAL for profitability analysis).")
    compare_at_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                           help_text="Original price for comparison if the item is on sale.")
    weight_grams = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text="Weight of the variant in grams.")
    inventory_quantity = models.IntegerField(
        help_text="Current stock level of this variant.")
    inventory_management = models.CharField(max_length=50, null=True, blank=True,
                                            help_text="How inventory is managed for this variant (e.g., 'shopify', 'blank').")
    metal_type = models.CharField(max_length=50, null=True, blank=True,
                                  help_text="e.g., 'Gold', 'Silver', 'Platinum'.")
    karat = models.CharField(max_length=10, null=True, blank=True,
                             help_text="e.g., '14K', '18K', '22K'.")
    stone_type = models.CharField(max_length=50, null=True, blank=True,
                                  help_text="e.g., 'Diamond', 'Ruby', 'Sapphire'.")
    # Raw option values from Shopify API
    option1 = models.CharField(max_length=255, null=True, blank=True)
    option2 = models.CharField(max_length=255, null=True, blank=True)
    option3 = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True,
                                      help_text="Timestamp when the variant was created in Shopify.")
    updated_at = models.DateTimeField(null=True, blank=True,
                                      help_text="Timestamp when the variant was last updated in Shopify.")

    def __str__(self):
        return f"{self.product.title} - {self.title}"

# 8. Order Table
class Order(models.Model):
    shopify_order_id = models.CharField(max_length=255, unique=True, primary_key=True)
    order_number = models.CharField(max_length=100)
    customer = models.ForeignKey(CustomerProfile, on_delete=models.SET_NULL, null=True, blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    financial_status = models.CharField(max_length=50, null=True, blank=True)
    fulfillment_status = models.CharField(max_length=50, null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)
    processed_at = models.DateTimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    shipping_city = models.CharField(max_length=100, null=True, blank=True)
    shipping_state = models.CharField(max_length=100, null=True, blank=True)
    shipping_country = models.CharField(max_length=100, null=True, blank=True)
    shipping_zip = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"Order #{self.order_number}"

# 9. OrderLineItem Table
class OrderLineItem(models.Model):
    shopify_line_item_id = models.CharField(max_length=255, unique=True, primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='line_items')
    product_detail = models.ForeignKey(ProductDetail, on_delete=models.SET_NULL, null=True, blank=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    variant_title = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    sku = models.CharField(max_length=100, null=True, blank=True)
    properties = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.title} in Order #{self.order.order_number}"

# 10. Transaction Table
class Transaction(models.Model):
    shopify_transaction_id = models.CharField(max_length=255, unique=True, primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    kind = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    gateway = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField()

    def __str__(self):
        return f"{self.kind} for Order #{self.order.order_number}"

# 11. InventoryLog Table
class InventoryLog(models.Model):
    CHANGE_TYPE_CHOICES = [
        ('restock', 'Restock'),
        ('damage', 'Damage'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('lost', 'Lost'),
        ('theft', 'Theft'),
    ]
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    quantity = models.IntegerField()
    reason = models.TextField(null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Improved __str__ for clarity
        return f"{self.change_type} {self.quantity} of {self.product_variant.title} on {self.changed_at.date()}"

# 12. LocalEvent Table
class LocalEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('festival', 'Festival'),
        ('public_holiday', 'Public Holiday'),
        ('local_sale_event', 'Local Sale Event'),
        ('season', 'Season'),
        ('strike', 'Strike'),
        ('weather_event', 'Weather Event'),
        ('economic_event', 'Economic Event'),
        ('other', 'Other'),
    ]
    name = models.CharField(max_length=150)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    influence = models.TextField(null=True, blank=True)
    demand_score = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.event_type})"

# 13. Collection Table
class Collection(models.Model):
    shopify_collection_id = models.CharField(max_length=255, unique=True, primary_key=True)
    title = models.CharField(max_length=255)
    handle = models.CharField(max_length=255, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

# 14. ProductCollection Table
class ProductCollection(models.Model):
    product = models.ForeignKey(ProductDetail, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product', 'collection')

    def __str__(self):
        return f"{self.product.title} in {self.collection.title}"

# 15. Supplier Table
class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    contact_person = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    average_lead_time_days = models.PositiveIntegerField(null=True, blank=True)
    minimum_order_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.name

# 16. ProductSupplier Table
class ProductSupplier(models.Model):
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    supplier_sku = models.CharField(max_length=100, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    lead_time_days = models.PositiveIntegerField(null=True, blank=True)
    minimum_order_quantity = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('product_variant', 'supplier')

    def __str__(self):
        return f"{self.product_variant.title} from {self.supplier.name}"