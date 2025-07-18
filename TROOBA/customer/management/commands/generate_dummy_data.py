#  python manage.py generate_dummy_data --num_locations 10 --num_customers 50 --num_products 30 --num_orders 100 --num_suppliers 5
# dummy data injection command 

import random
from datetime import timedelta, datetime
import pytz
import json
from decimal import Decimal # Import Decimal for precise calculations

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

# Import your models from the 'customer' app
from customer.models import (
    Location, CustomerProfile, ProductDetail, ProductImage, ProductOption,
    ProductOptionValue, ProductVariant, Order, OrderLineItem, Transaction,
    InventoryLog, LocalEvent, Collection, ProductCollection, Supplier, ProductSupplier
)

class Command(BaseCommand):
    help = 'Generates dummy data for the jewelry shop database.'

    def add_arguments(self, parser):
        parser.add_argument('--num_locations', type=int, default=5,
                            help='Number of dummy locations to create.')
        parser.add_argument('--num_customers', type=int, default=50,
                            help='Number of dummy customers to create.')
        parser.add_argument('--num_products', type=int, default=30,
                            help='Number of dummy products to create.')
        parser.add_argument('--num_orders', type=int, default=100,
                            help='Number of dummy orders to create.')
        parser.add_argument('--num_suppliers', type=int, default=5,
                            help='Number of dummy suppliers to create.')

    def handle(self, *args, **options):
        self.fake = Faker('en_IN') # Use Indian locale for more relevant data
        num_locations = options['num_locations']
        num_customers = options['num_customers']
        num_products = options['num_products']
        num_orders = options['num_orders']
        num_suppliers = options['num_suppliers']

        self.stdout.write(self.style.NOTICE("Starting dummy data generation..."))

        # Clear existing data (optional, but good for fresh runs)
        self.clear_data()

        # Generate Locations
        self.stdout.write("Generating Locations...")
        locations = self._generate_locations(num_locations)

        # Generate CustomerProfiles
        self.stdout.write("Generating Customer Profiles...")
        customers = self._generate_customer_profiles(num_customers, locations)

        # Generate Suppliers
        self.stdout.write("Generating Suppliers...")
        suppliers = self._generate_suppliers(num_suppliers)

        # Generate ProductDetails, Variants, Options, Images
        self.stdout.write("Generating Products and Variants...")
        products, variants = self._generate_products_and_variants(num_products, suppliers)

        # Generate Orders, Line Items, Transactions
        self.stdout.write("Generating Orders, Line Items, and Transactions...")
        self._generate_orders(num_orders, customers, variants)

        # Generate InventoryLogs
        self.stdout.write("Generating Inventory Logs...")
        self._generate_inventory_logs(variants)

        # Generate LocalEvents
        self.stdout.write("Generating Local Events...")
        self._generate_local_events(locations)

        # Generate Collections and ProductCollection links
        self.stdout.write("Generating Collections...")
        self._generate_collections(products)

        self.stdout.write(self.style.SUCCESS("Dummy data generation complete!"))

    def clear_data(self):
        self.stdout.write(self.style.WARNING("Clearing existing data..."))
        ProductSupplier.objects.all().delete()
        Supplier.objects.all().delete()
        ProductCollection.objects.all().delete()
        Collection.objects.all().delete()
        LocalEvent.objects.all().delete()
        InventoryLog.objects.all().delete()
        Transaction.objects.all().delete()
        OrderLineItem.objects.all().delete()
        Order.objects.all().delete()
        ProductVariant.objects.all().delete()
        ProductOptionValue.objects.all().delete()
        ProductOption.objects.all().delete()
        ProductImage.objects.all().delete()
        ProductDetail.objects.all().delete()
        CustomerProfile.objects.all().delete()
        Location.objects.all().delete()
        self.stdout.write(self.style.WARNING("Data cleared."))

    def _generate_locations(self, num):
        locations = []
        indian_cities = [
            ("Mumbai", "Maharashtra", 20000), ("Delhi", "Delhi", 18000),
            ("Bengaluru", "Karnataka", 15000), ("Hyderabad", "Telangana", 12000),
            ("Chennai", "Tamil Nadu", 10000), ("Kolkata", "West Bengal", 9000),
            ("Ahmedabad", "Gujarat", 8000), ("Pune", "Maharashtra", 7000),
            ("Jaipur", "Rajasthan", 6000), ("Surat", "Gujarat", 5000),
            ("Lucknow", "Uttar Pradesh", 4500), ("Chandigarh", "Punjab", 3000),
            ("Kochi", "Kerala", 3500), ("Goa", "Goa", 1000)
        ]

        for i in range(num):
            city_data = random.choice(indian_cities)
            city, state, density = city_data
            cultural_traits = {
                "Diwali": random.choice(["high_demand_gold", "moderate_demand"]),
                "Weddings": random.choice(["active", "seasonal"]),
                "Gift_giving": random.choice(["common", "occasional"])
            }
            loc = Location.objects.create(
                shopify_location_id=self.fake.unique.random_int(1000, 99999),
                city=city,
                state=state,
                country="India",
                region=random.choice(['North', 'South', 'East', 'West', 'Central']),
                cultural_traits=json.dumps(cultural_traits),
                population_density=density + self.fake.random_int(0, 5000),
                average_income=Decimal(self.fake.pydecimal(left_digits=7, right_digits=2, positive=True, min_value=300000, max_value=1500000))
            )
            locations.append(loc)
        return locations

    def _generate_customer_profiles(self, num, locations):
        customers = []
        gender_choices = ['Male', 'Female', 'Non-binary', 'Prefer not to say']
        age_ranges = ['18-24', '25-34', '35-44', '45-54', '55-64', '65+']
        purchase_styles = ['budget-conscious', 'luxury-seeker', 'gift-buyer', 'impulse', 'classic-buyer', 'modern-trendsetter']

        for i in range(num):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()
            email = self.fake.unique.email()
            phone = self.fake.phone_number()
            location = random.choice(locations)
            gender = random.choice(gender_choices)
            age_range = random.choice(age_ranges)
            purchase_style = random.choice(purchase_styles)
            accepts_marketing = self.fake.boolean(chance_of_getting_true=70)
            total_orders_count = self.fake.random_int(0, 20)
            total_spent = Decimal(self.fake.pydecimal(left_digits=6, right_digits=2, positive=True, min_value=1000, max_value=500000)) if total_orders_count > 0 else Decimal('0.00')
            created_at = self.fake.past_datetime(start_date='-2y', tzinfo=pytz.utc)
            updated_at = self.fake.date_time_between_dates(datetime_start=created_at, datetime_end='now', tzinfo=pytz.utc)

            customer = CustomerProfile.objects.create(
                shopify_customer_id=self.fake.unique.random_int(10000, 999999),
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                location=location,
                gender=gender,
                age_range=age_range,
                purchase_style=purchase_style,
                accepts_marketing=accepts_marketing,
                total_orders_count=total_orders_count,
                total_spent=total_spent,
                created_at=created_at,
                updated_at=updated_at,
            )
            customers.append(customer)
        return customers

    def _generate_products_and_variants(self, num, suppliers):
        products = []
        variants = []

        product_types = ['Ring', 'Necklace', 'Earrings', 'Bracelet', 'Pendant', 'Bangle', 'Jewelry Set']
        vendors = ['Tanishq', 'Malabar Gold & Diamonds', 'Joyalukkas', 'Kalyan Jewellers', 'PC Jeweller', 'Tribhovandas Bhimji Zaveri']
        metal_types = ['Gold', 'Silver', 'Platinum', 'Rose Gold', 'White Gold']
        karats = ['14K', '18K', '22K', '24K']
        stone_types = ['Diamond', 'Ruby', 'Emerald', 'Sapphire', 'Pearl', 'None']
        ring_sizes = ['6', '7', '8', '9', '10', 'Adjustable']
        necklace_lengths = ['16 inch', '18 inch', '20 inch']
        bracelet_lengths = ['6.5 inch', '7 inch', '7.5 inch']

        base_product_names = {
            'Ring': ['Solitaire Ring', 'Band Ring', 'Engagement Ring', 'Cocktail Ring', 'Daily Wear Ring'],
            'Necklace': ['Chain Necklace', 'Choker Necklace', 'Pendant Necklace', 'Layered Necklace'],
            'Earrings': ['Stud Earrings', 'Hoop Earrings', 'Drop Earrings', 'Jhumkas'],
            'Bracelet': ['Tennis Bracelet', 'Charm Bracelet', 'Cuff Bracelet'],
            'Pendant': ['Initial Pendant', 'Gemstone Pendant', 'Religious Pendant'],
            'Bangle': ['Traditional Bangle', 'Modern Bangle', 'Kada'],
            'Jewelry Set': ['Necklace & Earring Set', 'Bridal Set']
        }

        for i in range(num):
            product_type = random.choice(product_types)
            title = random.choice(base_product_names[product_type])
            vendor = random.choice(vendors)
            tags_list = [product_type.lower(), vendor.lower()]
            if product_type in ['Ring', 'Necklace', 'Earrings']:
                tags_list.append(random.choice(['bridal', 'daily wear', 'party wear']))
            if random.random() < 0.3:
                tags_list.append('new arrival')
            if random.random() < 0.2:
                tags_list.append('bestseller')

            created_at = self.fake.past_datetime(start_date='-1y', tzinfo=pytz.utc)
            updated_at = self.fake.date_time_between_dates(datetime_start=created_at, datetime_end='now', tzinfo=pytz.utc)
            published_at = updated_at if self.fake.boolean(chance_of_getting_true=90) else None

            product = ProductDetail.objects.create(
                shopify_product_id=self.fake.unique.random_int(100000, 9999999),
                title=f"{title} ({product_type})",
                handle=self.fake.slug(),
                vendor=vendor,
                product_type=product_type,
                status=random.choice(['active', 'draft']),
                tags=", ".join(tags_list),
                created_at=created_at,
                updated_at=updated_at,
                published_at=published_at,
            )
            products.append(product)

            # Generate Product Options and Values
            options_data = []
            if product_type in ['Ring', 'Necklace', 'Bracelet']:
                options_data.append({'name': 'Size', 'values': ring_sizes if product_type == 'Ring' else (necklace_lengths if product_type == 'Necklace' else bracelet_lengths)})
            if product_type != 'Jewelry Set': # Sets usually have fixed metal/stone combo
                options_data.append({'name': 'Metal Type', 'values': metal_types})
                options_data.append({'name': 'Karat', 'values': karats})
                if random.random() < 0.7: # Not all items have stones
                    options_data.append({'name': 'Stone Type', 'values': stone_types})

            product_options = []
            for j, opt_data in enumerate(options_data):
                option = ProductOption.objects.create(
                    product=product,
                    shopify_option_id=self.fake.unique.random_int(1000, 99999),
                    name=opt_data['name'],
                    position=j + 1
                )
                product_options.append(option)
                for k, val_str in enumerate(opt_data['values']):
                    ProductOptionValue.objects.create(
                        option=option,
                        value=val_str,
                        position=k + 1
                    )

            # Generate Product Variants
            # This logic creates combinations of options to form variants
            combinations = [[]]
            for opt in product_options:
                new_combinations = []
                for val in opt.values.all():
                    for combo in combinations:
                        new_combinations.append(combo + [(opt.name, val.value)])
                combinations = new_combinations

            for k, combo in enumerate(combinations):
                variant_title_parts = [v for n, v in combo]
                variant_title = " / ".join(variant_title_parts) if variant_title_parts else product.title
                metal = next((v for n, v in combo if n == 'Metal Type'), random.choice(metal_types))
                karat = next((v for n, v in combo if n == 'Karat'), random.choice(karats))
                stone = next((v for n, v in combo if n == 'Stone Type'), random.choice(stone_types))

                base_price = Decimal(self.fake.pydecimal(left_digits=5, right_digits=2, positive=True, min_value=5000, max_value=50000))

                # Corrected: Use Decimal objects for multiplication
                if 'Gold' in metal:
                    base_price *= Decimal('2') if '22K' in karat else Decimal('1.5')
                if 'Diamond' in stone:
                    base_price *= Decimal('3')
                
                price = base_price.quantize(Decimal('0.01')) # Ensure 2 decimal places

                # Corrected: Convert floats to Decimal before multiplication
                cost_price = (price * random.choice([Decimal('0.5'), Decimal('0.6'), Decimal('0.7')])).quantize(Decimal('0.01'))
                compare_at_price = (price * Decimal('1.2')).quantize(Decimal('0.01')) if self.fake.boolean(chance_of_getting_true=20) else None
                
                weight = Decimal(self.fake.pydecimal(left_digits=2, right_digits=2, positive=True, min_value=1.0, max_value=20.0))

                inventory_quantity = self.fake.random_int(0, 100)
                if inventory_quantity < 10:
                    inventory_quantity += 20 # Ensure some stock

                variant_created_at = self.fake.date_time_between_dates(datetime_start=created_at, datetime_end='now', tzinfo=pytz.utc)
                variant_updated_at = self.fake.date_time_between_dates(datetime_start=variant_created_at, datetime_end='now', tzinfo=pytz.utc)

                variant = ProductVariant.objects.create(
                    shopify_variant_id=self.fake.unique.random_int(1000000, 99999999),
                    product=product,
                    title=variant_title,
                    sku=f"{product.vendor[:3].upper()}-{product.product_type[:2].upper()}-{self.fake.unique.random_int(100,999)}",
                    price=price,
                    cost_price=cost_price,
                    compare_at_price=compare_at_price,
                    weight_grams=weight,
                    inventory_quantity=inventory_quantity,
                    inventory_management=random.choice(['shopify', None]),
                    metal_type=metal,
                    karat=karat,
                    stone_type=stone,
                    option1=variant_title_parts[0] if len(variant_title_parts) >= 1 else None,
                    option2=variant_title_parts[1] if len(variant_title_parts) >= 2 else None,
                    option3=variant_title_parts[2] if len(variant_title_parts) >= 3 else None,
                    created_at=variant_created_at,
                    updated_at=variant_updated_at,
                )
                variants.append(variant)

                # Link variant to a supplier
                ProductSupplier.objects.create(
                    product_variant=variant,
                    supplier=random.choice(suppliers),
                    supplier_sku=self.fake.unique.bothify(text='SUP-###-???'),
                    # Corrected: Convert float from random.uniform to string then Decimal
                    cost_price=(cost_price * Decimal(str(random.uniform(Decimal('0.9'), Decimal('1.1'))))).quantize(Decimal('0.01')),
                    lead_time_days=random.randint(7, 30)
                )


            # Add Product Image (at least one per product)
            ProductImage.objects.create(
                shopify_image_id=self.fake.unique.random_int(100000, 999999),
                product=product,
                src=self.fake.image_url(width=600, height=600),
                alt=f"{product.title} image",
                position=1,
                variant_ids=json.dumps([v.shopify_variant_id for v in variants if v.product == product])
            )

        return products, variants

    def _generate_orders(self, num, customers, variants):
        orders = []
        financial_statuses = ['paid', 'pending', 'refunded', 'voided']
        fulfillment_statuses = ['fulfilled', 'unfulfilled', 'partial']
        currencies = ['INR', 'USD'] # Assuming primary is INR, some USD if international

        for i in range(num):
            customer = random.choice(customers)
            processed_at = self.fake.past_datetime(start_date='-6m', tzinfo=pytz.utc)
            created_at = processed_at - timedelta(minutes=self.fake.random_int(1, 60))
            updated_at = self.fake.date_time_between_dates(datetime_start=created_at, datetime_end='now', tzinfo=pytz.utc)
            
            # Ensure at least one line item
            num_line_items = random.randint(1, 3)
            order_variants = random.sample(variants, min(num_line_items, len(variants)))
            
            total_price = sum(v.price * Decimal(str(self.fake.random_int(1,2))) for v in order_variants)
            
            order = Order.objects.create(
                shopify_order_id=self.fake.unique.random_int(100000, 9999999),
                order_number=f"#{self.fake.unique.random_int(10000, 99999)}",
                customer=customer,
                total_price=total_price,
                financial_status=random.choice(financial_statuses),
                fulfillment_status=random.choice(fulfillment_statuses),
                currency=random.choice(currencies),
                processed_at=processed_at,
                created_at=created_at,
                updated_at=updated_at,
                shipping_city=customer.location.city if customer.location else self.fake.city(),
                shipping_state=customer.location.state if customer.location else self.fake.state(),
                shipping_country=customer.location.country if customer.location else self.fake.country(),
                shipping_zip=self.fake.postcode(),
            )
            orders.append(order)

            for variant in order_variants:
                quantity = self.fake.random_int(1, 2)
                price = variant.price
                # Corrected: Ensure total_discount is Decimal
                total_discount = (price * Decimal(str(quantity)) * Decimal('0.1')).quantize(Decimal('0.01')) if self.fake.boolean(chance_of_getting_true=20) else Decimal('0.00')
                
                OrderLineItem.objects.create(
                    shopify_line_item_id=self.fake.unique.random_int(10000000, 999999999),
                    order=order,
                    product_detail=variant.product,
                    variant=variant,
                    title=variant.product.title,
                    variant_title=variant.title,
                    quantity=quantity,
                    price=price,
                    total_discount=total_discount,
                    sku=variant.sku,
                    properties=json.dumps({"engraving": self.fake.word()}) if self.fake.boolean(chance_of_getting_true=10) else ""
                )
                
                # Decrement inventory for sold items
                if order.financial_status == 'paid' and variant.inventory_management == 'shopify':
                    variant.inventory_quantity = max(0, variant.inventory_quantity - quantity)
                    variant.save()

            # Create a transaction for the order
            Transaction.objects.create(
                shopify_transaction_id=self.fake.unique.random_int(100000000, 9999999999),
                order=order,
                amount=order.total_price,
                kind='sale',
                status='success',
                gateway=random.choice(['razorpay', 'paypal', 'stripe', 'cod']),
                created_at=order.processed_at
            )
        return orders

    def _generate_inventory_logs(self, variants):
        change_types = [choice[0] for choice in InventoryLog.CHANGE_TYPE_CHOICES]
        for _ in range(len(variants) * 2): # Generate more logs than variants
            variant = random.choice(variants)
            change_type = random.choice(change_types)
            quantity = self.fake.random_int(1, 20)
            if change_type in ['damage', 'return', 'lost', 'theft', 'transfer_out']:
                quantity *= -1 # Represent decreases
                if variant.inventory_quantity + quantity < 0: # Avoid negative stock if it goes below 0
                    quantity = -variant.inventory_quantity
            
            reason = self.fake.sentence()
            changed_at = self.fake.past_datetime(start_date='-6m', tzinfo=pytz.utc)

            InventoryLog.objects.create(
                product_variant=variant,
                change_type=change_type,
                quantity=quantity,
                reason=reason,
                changed_at=changed_at
            )
            # Update variant's actual inventory for log
            variant.inventory_quantity += quantity
            variant.inventory_quantity = max(0, variant.inventory_quantity) # Inventory can't go below 0
            variant.save()


    def _generate_local_events(self, locations):
        event_types = [choice[0] for choice in LocalEvent.EVENT_TYPE_CHOICES]
        # Common Indian festivals/events
        indian_events = [
            ("Diwali", "festival", "2025-10-20", "2025-10-25", "High demand for gold and diamond jewelry."),
            ("Dussehra", "festival", "2025-10-02", "2025-10-04", "Moderate increase in demand."),
            ("Eid al-Fitr", "festival", "2025-03-30", "2025-04-01", "Demand for festive and gift jewelry."),
            ("Christmas", "public_holiday", "2025-12-24", "2025-12-26", "Increased demand for gift items."),
            ("New Year Sale", "local_sale_event", "2025-01-01", "2025-01-15", "Expected increase in sales due to discounts."),
            ("Monsoon Season", "season", "2025-06-01", "2025-09-30", "Slight dip in sales due to weather, but some demand for waterproof items."),
            ("Economic Downturn", "economic_event", "2025-05-01", "2025-12-31", "Reduced luxury spending, focus on essential or investment-grade jewelry."),
            ("Valentine's Day", "festival", "2025-02-14", "2025-02-14", "High demand for rings, pendants, and romantic gifts."),
            ("Wedding Season", "season", "2025-11-01", "2026-03-31", "Peak demand for bridal jewelry, heavy sets, and gold."),
        ]

        for name, event_type, start_date_str, end_date_str, influence_text in indian_events:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            location = random.choice(locations) if random.random() < 0.8 else None # Some events are national
            
            demand_score = random.randint(1, 10) # 1-10 scale
            if "high demand" in influence_text.lower() or "peak demand" in influence_text.lower():
                demand_score = random.randint(7, 10)
            elif "moderate" in influence_text.lower() or "increased demand" in influence_text.lower():
                demand_score = random.randint(5, 7)
            elif "dip" in influence_text.lower() or "reduced" in influence_text.lower():
                demand_score = random.randint(1, 4)

            LocalEvent.objects.create(
                name=name,
                event_type=event_type,
                start_date=start_date,
                end_date=end_date,
                location=location,
                influence=influence_text,
                demand_score=demand_score
            )
        
        # Add some random events too
        for _ in range(5):
            LocalEvent.objects.create(
                name=self.fake.catch_phrase(),
                event_type=random.choice(event_types),
                start_date=self.fake.date_between(start_date='-6m', end_date='+6m'),
                end_date=self.fake.date_between(start_date='-6m', end_date='+6m'),
                location=random.choice(locations),
                influence=self.fake.text(max_nb_chars=100),
                demand_score=self.fake.random_int(1,10)
            )

    def _generate_collections(self, products):
        collection_titles = ['Gold Collection', 'Diamond Essentials', 'Everyday Elegance',
                             'Bridal Collection', 'Men\'s Jewelry', 'Gift Ideas', 'New Arrivals']
        
        collections = []
        for title in collection_titles:
            collection = Collection.objects.create(
                shopify_collection_id=self.fake.unique.random_int(10000, 99999),
                title=title,
                handle=self.fake.slug(title),
                updated_at=self.fake.past_datetime(start_date='-3m', tzinfo=pytz.utc)
            )
            collections.append(collection)
        
        # Link products to collections
        for product in products:
            num_collections_for_product = random.randint(0, 2)
            assigned_collections = random.sample(collections, min(num_collections_for_product, len(collections)))
            for collection in assigned_collections:
                ProductCollection.objects.create(product=product, collection=collection)

    def _generate_suppliers(self, num):
        suppliers = []
        for i in range(num):
            supplier = Supplier.objects.create(
                name=self.fake.company(),
                contact_person=self.fake.name(),
                email=self.fake.email(),
                phone=self.fake.phone_number(),
                address=self.fake.address(),
                average_lead_time_days=self.fake.random_int(7, 45),
                minimum_order_value=Decimal(self.fake.pydecimal(left_digits=5, right_digits=2, positive=True, min_value=10000, max_value=100000))
            )
            suppliers.append(supplier)
        return suppliers