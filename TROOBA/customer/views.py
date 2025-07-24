import os
import requests
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from .models import Location, Customer, Product, ProductVariant, Order, OrderLineItem
from urllib.parse import parse_qs, urlparse
from django.shortcuts import render
SHOPIFY_STORE = os.getenv('SHOPIFY_STORE')
SHOPIFY_API_VERSION = os.getenv('SHOPIFY_API_VERSION')
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')

HEADERS = {
    'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
    'Content-Type': 'application/json'
}

def log(msg):
    print(f"[Shopify Fetch] {msg}")

def get_next_page_url(link_header):
    # Link header example:
    # <https://{store}/admin/api/2025-04/customers.json?limit=250&page_info=xyz>; rel="next"
    if not link_header:
        return None
    parts = link_header.split(',')
    for part in parts:
        if 'rel="next"' in part:
            url_part = part.split(';')[0].strip().strip('<>')
            return url_part
    return None

def fetch_shopify_data_all(endpoint):
    url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/{endpoint}?limit=250"
    all_items = []
    while url:
        log(f"Fetching: {url}")
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            log(f"Failed to fetch {url}: {response.status_code} - {response.text}")
            break
        data = response.json()
        # Extract main list key from endpoint, e.g. 'customers', 'orders', 'products', 'locations'
        key = endpoint.split('.')[0]  # crude way: 'customers.json' -> 'customers'
        items = data.get(key, [])
        log(f"Fetched {len(items)} items from current page.")
        all_items.extend(items)

        link_header = response.headers.get('Link')
        next_url = get_next_page_url(link_header)
        url = next_url  # if no next page, will be None and loop stops

    log(f"Total fetched from {endpoint}: {len(all_items)}")
    return all_items


@csrf_exempt
def fetch_and_store_all(request):
    # Locations
    locations = fetch_shopify_data_all('locations.json')
    for loc in locations:
        loc_obj, created = Location.objects.update_or_create(
            shopify_id=loc['id'],
            defaults={
                'name': loc['name'],
                'address': loc.get('address1') or '',
                'city': loc.get('city'),
                'region': loc.get('province'),
                'country': loc.get('country'),
            }
        )
        log(f"{'Created' if created else 'Updated'} Location: {loc_obj.name}")

    # Customers
    customers = fetch_shopify_data_all('customers.json')
    for cust in customers:
        name = (cust.get('first_name') or '') + ' ' + (cust.get('last_name') or '')
        cust_obj, created = Customer.objects.update_or_create(
            shopify_id=cust['id'],
            defaults={
                'email': cust.get('email'),
                'name': name.strip() or cust.get('email') or 'Unknown',
                'created_at': parse_datetime(cust['created_at']),
                'city': (cust.get('default_address') or {}).get('city'),
                'region': (cust.get('default_address') or {}).get('province'),
                'country': (cust.get('default_address') or {}).get('country'),
                'tags': cust.get('tags', '')
            }
        )
        log(f"{'Created' if created else 'Updated'} Customer: {cust_obj.name}")

    # Products and Variants
    products = fetch_shopify_data_all('products.json')
    for prod in products:
        prod_obj, created = Product.objects.update_or_create(
            shopify_id=prod['id'],
            defaults={
                'title': prod['title'],
                'product_type': prod.get('product_type'),
                'vendor': prod.get('vendor'),
                'tags': ','.join(prod.get('tags', [])) if isinstance(prod.get('tags'), list) else prod.get('tags', '')
            }
        )
        log(f"{'Created' if created else 'Updated'} Product: {prod_obj.title}")

        for variant in prod.get('variants', []):
            var_obj, v_created = ProductVariant.objects.update_or_create(
                shopify_id=variant['id'],
                defaults={
                    'product': prod_obj,
                    'title': variant.get('title'),
                    'sku': variant.get('sku'),
                    'price': float(variant.get('price') or 0),
                }
            )
            log(f"  {'Created' if v_created else 'Updated'} Variant: {var_obj.title}")

    # Orders and Line Items
    orders = fetch_shopify_data_all('orders.json')
    for order in orders:
        cust_obj = None
        if order.get('customer'):
            cust_obj = Customer.objects.filter(shopify_id=order['customer']['id']).first()

        location_obj = None
        if order.get('location_id'):
            location_obj = Location.objects.filter(shopify_id=order['location_id']).first()
        else:
            ship_addr = order.get('shipping_address')
            if ship_addr:
                location_obj = Location.objects.filter(city=ship_addr.get('city'), country=ship_addr.get('country')).first()

        order_obj, created = Order.objects.update_or_create(
            shopify_id=order['id'],
            defaults={
                'customer': cust_obj,
                'location': location_obj,
                'order_date': parse_datetime(order['created_at']),
                'day_of_week': parse_datetime(order['created_at']).strftime('%A') if order.get('created_at') else '',
                'season': '',  # optional logic here
                'time_slot': '', # optional logic here
                'total_price': float(order.get('total_price') or 0),
            }
        )
        log(f"{'Created' if created else 'Updated'} Order: {order_obj.shopify_id}")

        for item in order.get('line_items', []):
            prod_obj = Product.objects.filter(shopify_id=item['product_id']).first()
            var_obj = ProductVariant.objects.filter(shopify_id=item['variant_id']).first()
            OrderLineItem.objects.update_or_create(
                order=order_obj,
                variant=var_obj,
                defaults={
                    'product': prod_obj,
                    'quantity': item['quantity'],
                    'price': float(item['price']),
                    'product_type': item.get('product_type', ''),
                }
            )
            log(f"  Stored OrderLineItem for product {prod_obj.title if prod_obj else 'Unknown'}")

    return JsonResponse({'status': 'success', 'message': 'All Shopify data fetched and stored successfully.'})

# FEtching Data from API till this code 
# From now we will start the real process 

from django.http import JsonResponse
from django.db.models import Sum
from django.utils.timezone import make_aware
from datetime import datetime
from .models import OrderLineItem,Product,ProductVariant
from django.utils.safestring import mark_safe

def top_20_selling_products_till_2024_view(request):
    """
    Returns top 20 selling products (by quantity) before Jan 1, 2025.
    For each product, fetches the first matching variant via product_id.
    """
    cutoff_date = make_aware(datetime(2024, 1, 1))

    # Step 1: Aggregate top products
    top_products = (
        OrderLineItem.objects
        .filter(order__order_date__lt=cutoff_date)
        .values('product_id')
        .annotate(total_quantity_sold=Sum('quantity'))
        .order_by('-total_quantity_sold')[:20]
    )

    product_ids = [item['product_id'] for item in top_products]
    products_lookup = Product.objects.in_bulk(product_ids)

    # Step 2: Fetch variants grouped by product
    variants_by_product = {
        var.product_id: var
        for var in ProductVariant.objects.filter(product_id__in=product_ids)
    }

    # Step 3: Construct response
    results = []
    for item in top_products:
        product = products_lookup.get(item['product_id'])
        variant = variants_by_product.get(item['product_id'])

        results.append({
            "product_id": product.id if product else None,
            "product_shopify_id": product.shopify_id if product else None,
            "product_title": product.title if product else None,
            "variant_title": variant.title if variant else None,
            "variant_sku": variant.sku if variant else None,
            "price": variant.price if variant else None,
            "vendor": product.vendor if product else None,
            "product_type": product.product_type if product else None,
            "total_quantity_sold": item['total_quantity_sold'],
        })

    return render(request, 'customer/Top20.html', {
    'products': results,
    'products_json': mark_safe(json.dumps(results))
})


# 2025 Data fetching from 2024 top 20 products
import json
from datetime import datetime
from django.utils.timezone import make_aware
from django.db.models import Sum
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import OrderLineItem, Product, ProductVariant

@csrf_exempt
def top_20_selling_products_2024_onward_view(request):
    if request.method == 'POST':
        products_json = request.POST.get("products_json")

        if not products_json:
            return JsonResponse({"error": "Missing products_json in POST"}, status=400)

        if products_json.startswith("[{") and "'" in products_json and '"' not in products_json:
            products_json = products_json.replace("'", '"')

        try:
            top_products_2024 = json.loads(products_json)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

        variant_skus = [p.get('variant_sku') for p in top_products_2024 if p.get('variant_sku')]

        if not variant_skus:
            return JsonResponse({"error": "No valid variant SKUs provided"}, status=400)

        sku_order_map = {sku: i for i, sku in enumerate(variant_skus)}

        matching_variants = ProductVariant.objects.filter(sku__in=variant_skus)
        variant_id_map = {v.sku: v.id for v in matching_variants}
        variant_ids = list(variant_id_map.values())

        if not variant_ids:
            return JsonResponse({"error": "No matching variants found for given SKUs"}, status=400)

        # Timeline: Jan 1, 2024 to Dec 31, 2024
        start_date = make_aware(datetime(2024, 1, 1))
        end_date = make_aware(datetime(2025, 1, 1))

        items_2024_only = (
            OrderLineItem.objects
            .filter(
                order__order_date__gte=start_date,
                order__order_date__lt=end_date,
                variant_id__in=variant_ids
            )
            .values('product_id', 'variant_id')
            .annotate(total_quantity_sold=Sum('quantity'))
        )

        variant_sales_map = {item['variant_id']: item['total_quantity_sold'] for item in items_2024_only}
        products_lookup = Product.objects.in_bulk([item['product_id'] for item in items_2024_only])
        variants_lookup = ProductVariant.objects.in_bulk(variant_ids)

        results_unsorted = []
        for sku in variant_skus:
            vid = variant_id_map.get(sku)
            if vid is None:
                continue

            matching_item = next((item for item in items_2024_only if item['variant_id'] == vid), None)

            if matching_item:
                product = products_lookup.get(matching_item['product_id'])
                variant = variants_lookup.get(vid)
                total_qty = variant_sales_map.get(vid, 0)

                results_unsorted.append({
                    "product_id": product.id if product else None,
                    "product_shopify_id": product.shopify_id if product else None,
                    "product_title": product.title if product else None,
                    "variant_title": variant.title if variant else None,
                    "variant_sku": variant.sku if variant else None,
                    "price": variant.price if variant else None,
                    "vendor": product.vendor if product else None,
                    "product_type": product.product_type if product else None,
                    "total_quantity_sold": total_qty,
                })
            else:
                variant = variants_lookup.get(vid)
                results_unsorted.append({
                    "product_id": None,
                    "product_shopify_id": None,
                    "product_title": None,
                    "variant_title": variant.title if variant else None,
                    "variant_sku": variant.sku if variant else None,
                    "price": variant.price if variant else None,
                    "vendor": None,
                    "product_type": None,
                    "total_quantity_sold": 0,
                })

        return render(request, 'customer/Top202025.html', {'products': results_unsorted})

    return JsonResponse({"error": "Invalid method"}, status=405)
