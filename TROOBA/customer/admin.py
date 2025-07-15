from django.contrib import admin
from .models import (
    ProductDetail, ProductImage, ProductOption, ProductOptionValue,
    ProductVariant, Location, CustomerProfile, Order, OrderLineItem,
    Transaction, InventoryLog, LocalEvent, Collection, ProductCollection,
    Supplier, ProductSupplier
)

# --- Inlines for ProductDetail ---
class ProductImageInline(admin.TabularInline):
    """Inline for managing ProductImage related to ProductDetail."""
    model = ProductImage
    extra = 1 # Number of empty forms to display
    fields = ('src', 'alt', 'position', 'shopify_image_id')
    readonly_fields = ('shopify_image_id',)


class ProductOptionInline(admin.TabularInline):
    """Inline for managing ProductOption related to ProductDetail."""
    model = ProductOption
    extra = 1
    fields = ('name', 'position', 'shopify_option_id')
    readonly_fields = ('shopify_option_id',)


class ProductVariantInline(admin.TabularInline):
    """Inline for managing ProductVariant related to ProductDetail."""
    model = ProductVariant
    extra = 1 # Number of empty forms to display for new variants
    # Define fields to display in the inline form
    fields = (
        'title', 'sku', 'price', 'cost_price', 'compare_at_price',
        'weight_grams', 'inventory_quantity', 'metal_type', 'karat',
        'stone_type', 'option1', 'option2', 'option3'
    )
    # Fields that should not be editable directly in the inline
    readonly_fields = ('shopify_variant_id',)


# --- ModelAdmin for ProductDetail ---
@admin.register(ProductDetail)
class ProductDetailAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'product_type', 'vendor', 'status', 'shopify_product_id',
        'created_at', 'updated_at'
    )
    list_filter = ('product_type', 'vendor', 'status')
    search_fields = ('title', 'tags', 'sku') # Add sku for search if needed
    # Include the inlines defined above
    inlines = [
        ProductVariantInline,
        ProductImageInline,
        ProductOptionInline,
    ]
    # Fields to display in the main form for ProductDetail
    fields = (
        'title', 'handle', 'vendor', 'product_type', 'status', 'tags',
        'shopify_product_id', 'created_at', 'updated_at', 'published_at'
    )
    # Fields that should not be editable directly in the main form (e.g., timestamps)
    readonly_fields = ('shopify_product_id', 'created_at', 'updated_at', 'published_at')

# --- Registering other models with basic admin ---
admin.site.register(Location)
admin.site.register(CustomerProfile)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'total_price', 'financial_status', 'fulfillment_status', 'processed_at')
    list_filter = ('financial_status', 'fulfillment_status', 'created_at')
    search_fields = ('order_number', 'customer__email', 'customer__first_name', 'shipping_city')
    raw_id_fields = ('customer',) # Use a raw ID field for ForeignKey for better performance with many customers

@admin.register(OrderLineItem)
class OrderLineItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'title', 'variant_title', 'quantity', 'price', 'sku')
    list_filter = ('order__financial_status',) # Filter by order status
    search_fields = ('title', 'sku', 'order__order_number')
    raw_id_fields = ('order', 'product_detail', 'variant') # Use raw ID fields

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'kind', 'status', 'gateway', 'created_at')
    list_filter = ('kind', 'status', 'gateway')
    raw_id_fields = ('order',)

@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ('product_variant', 'change_type', 'quantity', 'changed_at')
    list_filter = ('change_type', 'changed_at')
    raw_id_fields = ('product_variant',)

@admin.register(LocalEvent)
class LocalEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_type', 'start_date', 'end_date', 'location')
    list_filter = ('event_type', 'location')
    search_fields = ('name', 'influence')

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'handle', 'updated_at')
    search_fields = ('title', 'handle')

@admin.register(ProductCollection)
class ProductCollectionAdmin(admin.ModelAdmin):
    list_display = ('product', 'collection')
    raw_id_fields = ('product', 'collection')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone')
    search_fields = ('name', 'contact_person', 'email')

@admin.register(ProductSupplier)
class ProductSupplierAdmin(admin.ModelAdmin):
    list_display = ('product_variant', 'supplier', 'cost_price', 'lead_time_days')
    raw_id_fields = ('product_variant', 'supplier')

# No need to register ProductOptionValue directly if it's managed via ProductOptionInline
# admin.site.register(ProductOptionValue) # This is typically not registered directly