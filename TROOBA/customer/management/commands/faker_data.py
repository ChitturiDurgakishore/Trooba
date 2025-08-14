from django.core.management.base import BaseCommand
from faker import Faker
from customer.models import Location, CustomerProfile, ProductDetail, ProductVariant, Order, OrderLineItem

class Command(BaseCommand):
    help = 'Populate the database with fake data for testing'

    def handle(self, *args, **kwargs):
        fake = Faker()

        def create_fake_locations(n=5):
            regions = ['North', 'South', 'East', 'West']
            for _ in range(n):
                Location.objects.create(
                    city=fake.city(),
                    state=fake.state(),
                    country='India',
                    region=fake.random_element(regions),
                    cultural_traits='{"festival": "Diwali", "demand": "High for gold"}',
                    population_density=fake.random_int(1000, 10000),
                    average_income=round(fake.random_number(digits=5), 2)
                )

        def create_fake_customers(n=10):
            locations = list(Location.objects.all())
            for _ in range(n):
                loc = fake.random_element(locations)
                CustomerProfile.objects.create(
                    shopify_customer_id=fake.uuid4(),
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    email=fake.unique.email(),
                    phone=fake.phone_number(),
                    location=loc,
                    gender=fake.random_element(['Male', 'Female', 'Other']),
                    age_range=fake.random_element(['18-24', '25-34', '35-44', '45-54']),
                    purchase_style=fake.random_element(['budget-conscious', 'luxury-seeker', 'impulse', 'gift-buyer']),
                    accepts_marketing=fake.boolean(),
                    total_orders_count=fake.random_int(0, 20),
                    total_spent=round(fake.random_number(digits=6), 2),
                    created_at=fake.date_time_this_year(),
                    updated_at=fake.date_time_this_year()
                )

        def create_fake_products(n=5):
            product_types = ['Ring', 'Necklace', 'Earrings', 'Bracelet', 'Pendant']
            metals = ['Gold', 'Silver', 'Platinum']
            stones = ['Diamond', 'Ruby', 'Sapphire', 'None']

            for _ in range(n):
                product = ProductDetail.objects.create(
                    shopify_product_id=fake.uuid4(),
                    title=fake.catch_phrase(),
                    handle=fake.slug(),
                    vendor=fake.company(),
                    product_type=fake.random_element(product_types),
                    status='active',
                    tags=",".join(fake.words(nb=3)),
                    created_at=fake.date_time_this_year(),
                    updated_at=fake.date_time_this_year(),
                    published_at=fake.date_time_this_year()
                )

                for i in range(fake.random_int(1, 3)):
                    ProductVariant.objects.create(
                        shopify_variant_id=fake.uuid4(),
                        product=product,
                        title=f"{product.title} Variant {i+1}",
                        sku=fake.unique.bothify(text='???-#####'),
                        price=round(fake.random_number(digits=5), 2),
                        cost_price=round(fake.random_number(digits=4), 2),
                        compare_at_price=round(fake.random_number(digits=5), 2),
                        weight_grams=round(fake.random_number(digits=2), 2),
                        inventory_quantity=fake.random_int(10, 100),
                        inventory_management='shopify',
                        metal_type=fake.random_element(metals),
                        karat=fake.random_element(['14K', '18K', '22K']),
                        stone_type=fake.random_element(stones),
                        option1='Default',
                        option2='Default',
                        option3='Default',
                        created_at=fake.date_time_this_year(),
                        updated_at=fake.date_time_this_year()
                    )

        def create_fake_orders(n=20):
            customers = list(CustomerProfile.objects.all())
            variants = list(ProductVariant.objects.all())

            for _ in range(n):
                customer = fake.random_element(customers)
                order = Order.objects.create(
                    shopify_order_id=fake.uuid4(),
                    order_number=fake.unique.random_int(min=1000, max=9999),
                    customer=customer,
                    total_price=0,
                    financial_status='paid',
                    fulfillment_status='fulfilled',
                    currency='INR',
                    processed_at=fake.date_time_this_year(),
                    created_at=fake.date_time_this_year(),
                    updated_at=fake.date_time_this_year(),
                    shipping_city=customer.location.city if customer.location else fake.city(),
                    shipping_state=customer.location.state if customer.location else fake.state(),
                    shipping_country=customer.location.country if customer.location else 'India',
                    shipping_zip=fake.postcode()
                )

                line_items_count = fake.random_int(1, 3)
                total_order_price = 0

                for _ in range(line_items_count):
                    variant = fake.random_element(variants)
                    quantity = fake.random_int(1, 5)
                    price = variant.price
                    line_total = price * quantity

                    OrderLineItem.objects.create(
                        shopify_line_item_id=fake.uuid4(),
                        order=order,
                        product_detail=variant.product,
                        variant=variant,
                        title=variant.title,
                        variant_title=variant.title,
                        quantity=quantity,
                        price=price,
                        total_discount=0,
                        sku=variant.sku,
                        properties=""
                    )

                    total_order_price += line_total

                order.total_price = total_order_price
                order.save()

        # Now call all
        create_fake_locations()
        create_fake_customers()
        create_fake_products()
        create_fake_orders()

        self.stdout.write(self.style.SUCCESS('Fake data created successfully!'))
