from django.http import HttpResponse

def home(request):
    return HttpResponse("Hello from TROOBA")

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
# top_20_selling_products_till_2024_view
# Gives data from April , May , June high sales 


# ----------------------------------------------------------------------------------------------------------------------------------

import logging
from django.db.models import Sum
from collections import defaultdict
import json
import re
import time
from datetime import datetime
from django.utils.timezone import make_aware
from django.shortcuts import render
import os
import requests
from dotenv import load_dotenv
from django.http import JsonResponse
from .models import ProductVariant, OrderLineItem, CustomerPromotion_April, CustomerPromotion_May, CustomerPromotion_June, Prompt, Product

# Set up a logger for debugging
logger = logging.getLogger(__name__)

def top_20_selling_products_till_2024_view(request):
    start_date = make_aware(datetime(2025, 4, 1))
    end_date = make_aware(datetime(2025, 7, 1))  # July not included

    # Step 1: Aggregate variant sales
    top_variants = (
        OrderLineItem.objects
        .filter(order__order_date__gte=start_date, order__order_date__lt=end_date)
        .values('variant_id')
        .annotate(total_quantity_sold=Sum('quantity'))
        .order_by('-total_quantity_sold')
    )

    # Step 2: Filter out 46349 quantities
    filtered_variants = [v for v in top_variants if v['total_quantity_sold'] != 46349]
    variant_ids_from_sales = [item['variant_id'] for item in filtered_variants]

    # Step 3: Fetch variant objects (skip empty SKUs)
    variants_qs = ProductVariant.objects.select_related('product').filter(id__in=variant_ids_from_sales).exclude(sku__isnull=True).exclude(sku='')
    variants = {v.id: v for v in variants_qs}

    results = []
    for item in filtered_variants:
        variant = variants.get(item['variant_id'])
        if not variant:
            continue
        product = variant.product
        results.append({
            "product_id": product.id if product else None,
            "product_shopify_id": product.shopify_id if product else None,
            "product_title": product.title if product else None,
            "variant_title": variant.title,
            "variant_sku": variant.sku,
            "price": variant.price,
            "vendor": product.vendor,
            "product_type": product.product_type,
            "total_quantity_sold": item['total_quantity_sold'],
        })
        if len(results) >= 5:
            break

    # ====== Prediction Begins Here ======
    
    # Step 4: Fetch promotional data and associate it with SKU
    # First, get the list of top-selling SKUs and their corresponding ProductVariant objects.
    variant_skus = [r["variant_sku"] for r in results if r["variant_sku"]]
    variant_objs = ProductVariant.objects.select_related('product').filter(sku__in=variant_skus)
    
    # Map the variant_id (primary key) to the ProductVariant object for later use
    variant_id_map = {v.id: v for v in variant_objs}
    
    # Get the list of shopify_ids for the top-selling variants, this is what's in the promotion tables.
    top_variant_shopify_ids = [v.shopify_id for v in variant_objs]

    # This dictionary will store the final promotional data keyed by SKU
    promo_data_by_sku = defaultdict(dict)
    
    # This dictionary is a temporary map from shopify_id to SKU to simplify the loop below
    shopify_id_to_sku_map = {v.shopify_id: v.sku for v in variant_objs}

    promo_models = {
        '2025-04': CustomerPromotion_April,
        '2025-05': CustomerPromotion_May,
        '2025-06': CustomerPromotion_June,
    }

    for month, model in promo_models.items():
        # Query promotion records using the shopify_id as the filter
        promo_qs = model.objects.filter(variant_id__in=top_variant_shopify_ids)
        for promo in promo_qs:
            shopify_id = promo.variant_id
            variant_sku = shopify_id_to_sku_map.get(shopify_id)
            if variant_sku:
                promo_data_by_sku[variant_sku][month] = {
                    'impressions': promo.impressions,
                    'clicks': promo.clicks,
                    'revenue': float(promo.revenue or 0),
                    'units_sold': promo.units_sold,
                }
                logger.debug(f"Promo data for SKU {variant_sku} in {month}: {promo_data_by_sku[variant_sku][month]}")

    # Historical sales April–June 2025
    monthly_sales = defaultdict(lambda: defaultdict(int))
    order_items = OrderLineItem.objects.filter(
        variant_id__in=variant_ids_from_sales,
        order__order_date__gte=start_date,
        order__order_date__lt=end_date
    )
    for item in order_items:
        month = item.order.order_date.strftime('%Y-%m')
        # Use the variant_id map to get the SKU
        variant_obj = variant_id_map.get(item.variant_id)
        if variant_obj:
            monthly_sales[variant_obj.sku][month] += item.quantity

    # Actual July sales
    july_start = make_aware(datetime(2025, 7, 1))
    aug_start = make_aware(datetime(2025, 8, 1))
    actual_july_sales = defaultdict(int)
    july_orders = OrderLineItem.objects.filter(
        variant_id__in=variant_ids_from_sales,
        order__order_date__gte=july_start,
        order__order_date__lt=aug_start
    )
    for item in july_orders:
        variant_obj = variant_id_map.get(item.variant_id)
        if variant_obj:
            actual_july_sales[variant_obj.sku] += item.quantity

    # Load Gemini API Key
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return render(request, "customer/predictions.html", {"predictions": [], "error": "GEMINI_API_KEY missing"})

    try:
        prompt_template = Prompt.objects.get(type='MainPrompt').prompt.strip()
    except Prompt.DoesNotExist:
        return render(request, "customer/predictions.html", {"predictions": [], "error": "Prompt with type=MainPrompt not found"})

    def call_gemini(prompt_text):
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": GEMINI_API_KEY
        }
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "temperature": 0.0,
                "topK": 1,
                "topP": 0.9
            }
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            logger.error(f"Gemini API Error: {str(e)}")
            return f"[Gemini Error] {str(e)}"

    predictions = []
    for sku in variant_skus:
        variant = variant_objs.get(sku=sku)
        if not variant:
            continue
        product = variant.product
        sales_data = monthly_sales.get(sku, {})
        promo_data = promo_data_by_sku.get(sku, {})

        prompt = f"""{prompt_template}
        ### PRODUCT DETAILS
        Title: {product.title}
        SKU: {sku}
        Type: {product.product_type}
        Vendor: {product.vendor}

        ### HISTORICAL SALES (Apr–Jun 2025)
        {json.dumps(sales_data, indent=2)}

        ### PROMOTION SUMMARY (Apr–Jun 2025)
        {json.dumps(promo_data, indent=2)}

        Q: Based on the above data, what is the expected quantity sold in July 2025?
        Return only the number and a short reason explaining your logic."""

        gemini_response = call_gemini(prompt)
        actual_qty = actual_july_sales.get(sku, 0)

        lines = gemini_response.strip().splitlines()
        predicted_qty = None
        reason_lines = []

        for line in lines:
            match = re.search(r"[Ff]orecast[:\s\*]*([0-9]{1,3})\b", line)
            if match:
                predicted_qty = int(match.group(1))
                break

        if predicted_qty is None:
            for line in lines:
                numbers = [int(n) for n in re.findall(r"\b\d+\b", line)]
                valid_numbers = [n for n in numbers if n < 500]
                if valid_numbers:
                    predicted_qty = max(valid_numbers)

        if predicted_qty is None:
            predicted_qty = 0

        for line in lines:
            if any(c.isalpha() for c in line):
                reason_lines.append(line)
        reason = " ".join(reason_lines).strip() if reason_lines else "N/A"

        predictions.append({
            "SKU": sku,
            "Product": product.title,
            "Past Sales": {
                "2025-04": sales_data.get("2025-04", 0),
                "2025-05": sales_data.get("2025-05", 0),
                "2025-06": sales_data.get("2025-06", 0),
            },
            "Predicted July Sales": predicted_qty,
            "Actual July Sales": actual_qty,
            "Reason": reason,
        })
        time.sleep(1.2)

    return render(request, "customer/predictions.html", {"predictions": predictions})

# Directly gets the highest sales in April , May , June month and then predicts using gemini then compares with original data





# -------------------------------

import os
import json
import requests
from collections import defaultdict
from datetime import datetime
from django.shortcuts import render
from django.utils.timezone import make_aware
from dotenv import load_dotenv
from .models import ProductVariant, OrderLineItem, Prompt  # 👈 include Prompt model

def compare_sku_prediction_view(request, sku):
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    if not GEMINI_API_KEY:
        return render(request, 'customer/compare.html', {'error': 'Gemini API Key not found in environment variables.'})

    variant = ProductVariant.objects.select_related('product').filter(sku=sku).first()
    if not variant or not variant.product:
        return render(request, 'customer/compare.html', {'error': 'Invalid SKU or product not found.'})

    product = variant.product

    # Step 1: Historical sales before 2024
    cutoff = make_aware(datetime(2024, 1, 1))
    sales_qs = OrderLineItem.objects.filter(variant=variant, order__order_date__lt=cutoff)
    monthly_history = defaultdict(int)
    for item in sales_qs:
        month_str = item.order.order_date.strftime('%Y-%m')
        monthly_history[month_str] += item.quantity

    history_list = [{"month": m, "quantity": q} for m, q in sorted(monthly_history.items())]

    # Step 2: Fetch Prompt Header and MainPrompt from database
    header = Prompt.objects.filter(type="Header").first()
    main_rules = Prompt.objects.filter(type="MainPrompt").first()

    if not header or not main_rules:
        return render(request, 'customer/compare.html', {'error': 'Prompt instructions missing in database.'})

    # Step 3: Build prompt dynamically
    def build_prompt(sku, title, history):
        return f"""

{main_rules.prompt}
---

### PRODUCT DETAILS:
- Product Name: "{title}"
- SKU: {sku}
- Today's Date: January 1, 2024
- Product Category: Fashion Jewellery (non-essential)
- Region: India

---
---

### OUTPUT FORMAT (STRICT JSON ONLY):

{{
  "sku": "{sku}",
  "monthly_sales_2024": {{
    "January": <integer>,
    "February": <integer>,
    "March": <integer>,
    "April": <integer>,
    "May": <integer>,
    "June": <integer>,
    "July": <integer>,
    "August": <integer>,
    "September": <integer>,
    "October": <integer>,
    "November": <integer>,
    "December": <integer>
  }},
  "total_predicted_quantity_2024": <integer>,
  "reasoning": "<Strict explanation for predicted quantities: highlight key months, explain decay if any, avoid vague phrases>"
}}

---

### HISTORICAL SALES DATA:
{json.dumps(history, indent=2)}
"""

    # Step 4: Call Gemini
    prediction_data = {
        "monthly_sales_2024": {},
        "total_predicted_quantity_2024": 0,
        "reasoning": "[Gemini Error] No prediction due to API failure."
    }

    try:
        prompt_text = build_prompt(sku, product.title, history_list)

        response = requests.post(
            GEMINI_URL,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": GEMINI_API_KEY,
            },
            data=json.dumps({
                "contents": [
                    {
                        "parts": [{"text": prompt_text}]
                    }
                ]
            })
        )

        response.raise_for_status()
        data = response.json()

        if 'candidates' in data and data['candidates']:
            content = data['candidates'][0]['content']['parts'][0]['text'].strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").strip()
            if content.endswith("```"):
                content = content[:-3].strip()
            prediction_data = json.loads(content)

    except requests.exceptions.HTTPError as e:
        prediction_data["reasoning"] = f"[Gemini HTTP Error] {e.response.status_code} {e.response.reason}: {e.response.text}"
    except requests.exceptions.RequestException as e:
        prediction_data["reasoning"] = f"[Gemini Request Error] {str(e)}"
    except json.JSONDecodeError as e:
        prediction_data["reasoning"] = f"[Gemini Response Parsing Error] Invalid JSON: {str(e)}"
    except Exception as e:
        prediction_data["reasoning"] = f"[Unexpected Error] {str(e)}"

    # Step 5: Actual 2024 sales
    jan_2024 = make_aware(datetime(2024, 1, 1))
    jan_2025 = make_aware(datetime(2025, 1, 1))

    actual_qs = OrderLineItem.objects.filter(
        variant=variant,
        order__order_date__gte=jan_2024,
        order__order_date__lt=jan_2025
    )

    actual_by_month = defaultdict(int)
    for item in actual_qs:
        month = item.order.order_date.strftime('%B')
        actual_by_month[month] += item.quantity

    # Step 6: Build comparison list
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]

    comparison = []
    for m in months:
        comparison.append({
            "month": m,
            "predicted": prediction_data.get("monthly_sales_2024", {}).get(m, 0),
            "actual": actual_by_month.get(m, 0)
        })

    total_actual = sum([row["actual"] for row in comparison])

    return render(request, 'customer/monthly_comparison.html', {
        "product_title": product.title,
        "variant_title": variant.title,
        "sku": sku,
        "comparison": comparison,
        "total_predicted": prediction_data.get("total_predicted_quantity_2024", 0),
        "total_actual": total_actual,
        "reasoning": prediction_data.get("reasoning", "")
    })



from django.http import JsonResponse
from django.utils.timezone import make_aware
from datetime import datetime
from .models import ProductVariant, OrderLineItem
from collections import defaultdict

def sku_sales_history(request, sku):
    variant = ProductVariant.objects.select_related('product').filter(sku=sku).first()
    if not variant:
        return JsonResponse({'error': 'Invalid SKU'}, status=404)

    cutoff_date = make_aware(datetime(2024, 1, 1))

    sales_qs = OrderLineItem.objects.filter(
        variant=variant,
        order__order_date__lt=cutoff_date
    ).select_related('order')

    daily_sales = defaultdict(lambda: {"quantity": 0, "total_amount": 0.0})
    
    for item in sales_qs:
        date_str = item.order.order_date.strftime('%Y-%m-%d')
        daily_sales[date_str]["quantity"] += item.quantity
        daily_sales[date_str]["total_amount"] += item.price * item.quantity

    history = [
        {"date": date, "quantity": data["quantity"], "total_amount": round(data["total_amount"], 2)}
        for date, data in sorted(daily_sales.items())
    ]

    return JsonResponse({
        "sku": sku,
        "variant_title": variant.title,
        "product_title": variant.product.title if variant.product else "",
        "history": history
    }, status=200)


#2023 data shown , 2024 data shown , comparison shown for every SKU varient . 
 
# Change ony this function for any changes 
