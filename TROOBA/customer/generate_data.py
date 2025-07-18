import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime
import random
from tqdm import tqdm

# --- CONFIGURATION ---
NUM_CUSTOMERS = 500
NUM_PRODUCTS = 100
NUM_ORDERS = 2000
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2025, 7, 15)

# --- REALISTIC DATA SETS FOR JEWELLERY ---
PRODUCT_TYPES = ['Ring', 'Necklace', 'Earrings', 'Bracelet', 'Bangle', 'Pendant']
METAL_TYPES = ['Gold', 'Silver', 'Platinum', 'Rose Gold']
STONE_TYPES = ['Diamond', 'Ruby', 'Sapphire', 'Emerald', 'Pearl', 'None']
KARATS = ['14K', '18K', '22K', '24K']
LOCATIONS = [
    {'city': 'Mumbai', 'state': 'Maharashtra', 'region': 'West'},
    {'city': 'Delhi', 'state': 'Delhi', 'region': 'North'},
    {'city': 'Chennai', 'state': 'Tamil Nadu', 'region': 'South'},
    {'city': 'Kolkata', 'state': 'West Bengal', 'region': 'East'},
    {'city': 'Hyderabad', 'state': 'Telangana', 'region': 'South'}
]
FESTIVAL_DATES = {
    "Dhanteras_2023": (datetime(2023, 11, 10), 1.8),
    "Diwali_2023": (datetime(2023, 11, 12), 2.5),
    "Akshaya_Tritiya_2024": (datetime(2024, 5, 10), 2.2),
    "Dhanteras_2024": (datetime(2024, 10, 29), 1.8),
    "Diwali_2024": (datetime(2024, 11, 1), 2.5),
}
WEDDING_SEASON_MONTHS = [11, 12, 1, 2]

fake = Faker('en_IN')

def generate_products_and_variants():
    products = []
    variants = []
    for i in range(1, NUM_PRODUCTS + 1):
        prod_type = random.choice(PRODUCT_TYPES)
        metal = random.choice(METAL_TYPES)
        stone = random.choice(STONE_TYPES)
        title = f"{metal} {stone} {prod_type}" if stone != 'None' else f"Classic {metal} {prod_type}"

        created_at = fake.date_time_between(start_date='-3y', end_date='-1y')
        updated_at = fake.date_time_between(start_date=created_at, end_date='now')
        published_at = fake.date_time_between(start_date=created_at, end_date=updated_at)

        products.append({
            'id': i,
            'shopify_product_id': f'gid://shopify/Product/{1000 + i}',
            'title': title,
            'vendor': fake.company(),
            'product_type': prod_type,
            'status': 'active',
            'tags': f"{prod_type},{metal},{stone}",
            'created_at': created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'published_at': published_at.strftime('%Y-%m-%d %H:%M:%S'),
        })

        for j in range(random.randint(1, 3)):
            karat = random.choice(KARATS) if metal in ['Gold', 'Rose Gold'] else None
            size = random.randint(5, 12) if prod_type == 'Ring' else None
            variant_title = f"{karat or ''} / Size {size or 'One Size'}".strip(" /")
            base_price = (10000 if metal == 'Silver' else 50000 if metal == 'Gold' else 80000) * (1 + (KARATS.index(karat) * 0.5 if karat else 0))

            variants.append({
                'shopify_variant_id': f'gid://shopify/ProductVariant/{10000 + len(variants)}',
                'productdetail_id': i,
                'title': variant_title,
                'sku': f"{prod_type[:3].upper()}-{metal[:2].upper()}-{i}-{j}-{random.randint(1,999)}",
                'price': round(random.uniform(base_price * 0.9, base_price * 1.2), 2),
                'cost_price': round(base_price * 0.6, 2),
                'compare_at_price': None,
                'weight_grams': round(random.uniform(2.0, 20.0), 2),
                'inventory_quantity': random.randint(5, 50),
                'inventory_management': None,
                'metal_type': metal,
                'karat': karat,
                'stone_type': stone,
                'option1': None,
                'option2': None,
                'option3': None,
                'created_at': fake.date_time_between(start_date='-3y', end_date='-1y').strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': fake.date_time_between(start_date='-1y', end_date='now').strftime('%Y-%m-%d %H:%M:%S'),
            })
    return pd.DataFrame(products), pd.DataFrame(variants)


def generate_customers():
    customers = []
    for i in range(1, NUM_CUSTOMERS + 1):
        created_at = fake.date_time_between(start_date='-3y', end_date='-1y')
        updated_at = fake.date_time_between(start_date=created_at, end_date='now')

        customers.append({
            'id': i,
            'shopify_customer_id': f'gid://shopify/Customer/{5000 + i}',
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'email': fake.unique.email(),
            'phone': fake.phone_number(),
            'location_id': random.randint(1, len(LOCATIONS)),
            'gender': random.choice(['Male', 'Female', 'Other', None]),
            'age_range': random.choice(['18-24', '25-34', '35-44', '45-54', '55+']),
            'purchase_style': random.choice(['budget-conscious', 'luxury-seeker', 'gift-buyer', 'trendy']),
            'accepts_marketing': fake.boolean(chance_of_getting_true=50),
            'total_orders_count': random.randint(0, 20),
            'total_spent': round(random.uniform(1000, 50000), 2),
            'created_at': created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    return pd.DataFrame(customers)


def get_sales_probability(date):
    prob = 1.0
    if date.weekday() >= 5:
        prob *= 1.5
    if date.month in WEDDING_SEASON_MONTHS:
        prob *= 1.8
    for event, (event_date, multiplier) in FESTIVAL_DATES.items():
        if abs((date - event_date).days) <= 2:
            prob *= multiplier
    return prob


def generate_orders_and_line_items(customers_df, variants_df, products_df, locations_df):
    orders = []
    line_items = []
    date_range = pd.date_range(START_DATE, END_DATE)

    order_id_counter = 1
    with tqdm(total=NUM_ORDERS, desc="Generating Orders") as pbar:
        while order_id_counter <= NUM_ORDERS:
            sale_date = random.choice(date_range)
            if random.random() > get_sales_probability(sale_date) / 10:
                continue

            customer = customers_df.sample(1).iloc[0]
            num_items = np.random.choice([1, 2, 3], p=[0.7, 0.2, 0.1])

            order_total = 0

            for _ in range(num_items):
                variant = variants_df.sample(1).iloc[0]
                quantity = 1
                price = variant['price']
                order_total += price * quantity

                line_items.append({
                    'shopify_line_item_id': f'gid://shopify/LineItem/{80000 + len(line_items)}',
                    'order_id': order_id_counter,
                    'productdetail_id': variant['productdetail_id'],
                    'variant_id': variant['shopify_variant_id'],
                    'title': products_df.loc[products_df['id'] == variant['productdetail_id'], 'title'].values[0],
                    'variant_title': variant['title'],
                    'quantity': quantity,
                    'price': price,
                    'sku': variant['sku']
                })

            orders.append({
                'shopify_order_id': f'gid://shopify/Order/{30000 + order_id_counter}',
                'order_number': 1000 + order_id_counter,
                'customer_id': customer['id'],
                'total_price': round(order_total, 2),
                'financial_status': 'paid',
                'fulfillment_status': 'fulfilled',
                'processed_at': sale_date.strftime('%Y-%m-%d %H:%M:%S'),
                'shipping_city': locations_df.loc[locations_df['id'] == customer['location_id'], 'city'].values[0]
            })
            order_id_counter += 1
            pbar.update(1)

    return pd.DataFrame(orders), pd.DataFrame(line_items)


def df_to_sql_insert(df, table_name):
    sql_texts = []
    for _, row in df.iterrows():
        cols = ', '.join([f"`{col}`" for col in row.index])
        vals = ', '.join([f"'{str(v).replace('\'', '\'\'')}'" if pd.notna(v) else 'NULL' for v in row.values])
        sql_texts.append(f"INSERT INTO `{table_name}` ({cols}) VALUES ({vals});")
    return '\n'.join(sql_texts)


print("🚀 Starting realistic data generation for Jewellery Store...")

print("1. Generating Locations...")
locations_df = pd.DataFrame(LOCATIONS)
locations_df['id'] = range(1, len(locations_df) + 1)

print("2. Generating Products and Variants...")
products_df, variants_df = generate_products_and_variants()

print("3. Generating Customers...")
customers_df = generate_customers()

print("4. Simulating Sales Orders (this may take a moment)...")
orders_df, line_items_df = generate_orders_and_line_items(customers_df, variants_df, products_df, locations_df)

print("5. Converting data to SQL INSERT statements...")

sql_output = ""
sql_output += df_to_sql_insert(locations_df, 'customer_location') + '\n\n'
sql_output += df_to_sql_insert(products_df, 'customer_productdetail') + '\n\n'
sql_output += df_to_sql_insert(variants_df, 'customer_productvariant') + '\n\n'
sql_output += df_to_sql_insert(customers_df, 'customer_table') + '\n\n'
sql_output += df_to_sql_insert(orders_df, 'customer_orders') + '\n\n'
sql_output += df_to_sql_insert(line_items_df, 'customer_orderlineitem') + '\n\n'

output_filename = "jewellery_data.sql"
with open(output_filename, 'w', encoding='utf-8') as f:
    f.write(sql_output)

print(f"\n🎉 Success! Your realistic dataset has been generated.")
print(f"✅ Your file is ready: {output_filename}")
