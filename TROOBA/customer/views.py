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
from django.shortcuts import render
from django.utils.safestring import mark_safe
import json

from .models import OrderLineItem, Product, ProductVariant

def top_20_selling_products_till_2024_view(request):
    """
    Returns top 20 selling variants (by quantity) before Jan 1, 2024.
    Purely based on variant_id, not product_id.
    """
    cutoff_date = make_aware(datetime(2024, 1, 1))

    # Step 1: Aggregate top variants
    top_variants = (
        OrderLineItem.objects
        .filter(order__order_date__lt=cutoff_date)
        .values('variant_id')
        .annotate(total_quantity_sold=Sum('quantity'))
        .order_by('-total_quantity_sold')[:20]
    )

    variant_ids = [item['variant_id'] for item in top_variants]
    variants = ProductVariant.objects.select_related('product').in_bulk(variant_ids)

    # Step 2: Build result maintaining order
    results = []
    for item in top_variants:
        variant = variants.get(item['variant_id'])
        product = variant.product if variant else None

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


# Testing
import os
import json
import requests
from dotenv import load_dotenv
from django.http import JsonResponse

def test_gemini_api(request):
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        return JsonResponse({"error": "GEMINI_API_KEY not found in .env"}, status=500)

    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Explain how AI works in a few words"
                    }
                ]
            }
        ]
    }

    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }

    try:
        response = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return JsonResponse({"status": response.status_code, "response": response.json()})
    except requests.exceptions.HTTPError as e:
        return JsonResponse({
            "error": f"{e.response.status_code} Client Error",
            "details": e.response.text
        }, status=e.response.status_code)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)





# Data fetched fron API , Top 20 items also shown . 2023 data and 2024 data 
# From here we will predict the 2024 year saled based on data histroy till 2024 Jan 1 . 
# 24-07-2025


import json
import os
import time
import requests
from datetime import datetime
from collections import defaultdict
from django.http import JsonResponse
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

from .models import OrderLineItem, ProductVariant, Product

@csrf_exempt
def fetch_historical_sales_till_2024(request):
    """
    Given a list of variant SKUs, returns:
    - Total quantity sold for each SKU (till Jan 1, 2024)
    - Detailed sales history (daily)
    - OpenAI GPT-4o monthly sales predictions for 2024 (fashion jewellery)
      using aggregated monthly sales history to reduce prompt size.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    variant_skus_json = request.POST.get('variant_skus_json')
    if not variant_skus_json:
        return JsonResponse({'error': 'Missing variant_skus_json in POST'}, status=400)

    try:
        variant_skus = json.loads(variant_skus_json)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)

    if not variant_skus:
        return JsonResponse({'error': 'No variant SKUs provided'}, status=400)

    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        return JsonResponse({'error': 'Missing OPENAI_API_KEY in .env'}, status=500)

    OPENAI_URL = "https://api.openai.com/v1/chat/completions"

    variants = ProductVariant.objects.select_related('product').filter(sku__in=variant_skus)
    variant_lookup = {v.sku: v for v in variants}
    variant_ids = [v.id for v in variants]

    if not variant_ids:
        return JsonResponse({'error': 'No matching variants found'}, status=400)

    cutoff_date = make_aware(datetime(2024, 1, 1))

    sales_qs = (
        OrderLineItem.objects
        .filter(variant_id__in=variant_ids, order__order_date__lt=cutoff_date)
        .select_related('order', 'variant', 'product')
    )

    sales_data_by_sku = {}
    total_qty_per_sku = {}
    monthly_sales_by_sku = defaultdict(lambda: defaultdict(int))  # {sku: {month_str: qty}}

    for item in sales_qs:
        sku = item.variant.sku if item.variant else None
        if not sku:
            continue

        date_str = item.order.order_date.strftime('%Y-%m-%d')
        month_str = item.order.order_date.strftime('%Y-%m')

        sales_data_by_sku.setdefault(sku, []).append({
            "date": date_str,
            "quantity": item.quantity,
            "price": item.price,
            "product_title": item.product.title if item.product else None,
            "variant_title": item.variant.title if item.variant else None,
            "product_type": item.product.product_type if item.product else None,
            "vendor": item.product.vendor if item.product else None,
        })

        monthly_sales_by_sku[sku][month_str] += item.quantity
        total_qty_per_sku[sku] = total_qty_per_sku.get(sku, 0) + item.quantity

    def monthly_sales_to_list(monthly_dict):
        months_sorted = sorted(monthly_dict.keys())
        return [{"month": m, "quantity": monthly_dict[m]} for m in months_sorted]

    def build_prompt(sku, title, monthly_history):
     return f"""
You are an advanced AI trained in **retail forecasting**, specializing in **fashion jewellery sales in India**. Your task is to estimate monthly sales for 2024 for a given SKU, based solely on its historical monthly sales up to Jan 1, 2024.

---

## CONTEXT:
Fashion jewellery sales behave differently than staples:
- **Highly trend-driven** with sudden spikes or drops
- **Seasonality** is tied to **festivals, weddings**, and **promotions**
- A product’s success depends on **visibility, influencer campaigns**, **SKU lifecycle**, and **pricing**
- **Long tail behavior**: Some SKUs have low but stable sales
- **Zero or declining sales** should be interpreted realistically — not smoothed over

---

## INPUT PRODUCT:
- Product Title: "{title}"
- SKU: {sku}
- Product Category: Fashion Jewellery (non-essential)
- Region: India
- Forecasting Year: 2024
- Today's Date: January 1, 2024

---

## MODELING PRINCIPLES:
1. Use **actual monthly sales patterns** to understand trends.
2. If sales are **declining or zero for multiple months**, treat it as SKU decline unless strong festive pattern exists.
3. DO NOT assume uniform sales unless the SKU had consistent historical demand.
4. If spikes were **promotion-driven** or **seasonal**, do not project them forward unless that event recurs.
5. It's okay to predict **0 sales** for multiple months — accuracy matters over optimism.
6. Consider **Indian jewellery demand peaks** (weddings, Diwali, Rakhi, Akshaya Tritiya).
7. Follow **data-driven judgment** — do not "fill" missing months with average.

---

## FESTIVE CALENDAR (India, 2024):
- Feb: Valentine’s Day → minor uplift
- Mar: Holi, Women’s Day
- Apr: Akshaya Tritiya → **high spike possible**
- May–June: Summer Weddings
- Aug: Raksha Bandhan, Onam
- Oct: Dussehra
- Nov: Karwa Chauth, Diwali → **major spike**
- Dec: Winter Weddings, Christmas

---

## OUTPUT FORMAT:
Return a strict JSON format only. No explanations outside JSON. Structure:

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
  "reasoning": "<Short reasoning: explain seasonality effects, SKU lifecycle, sales pattern, and confidence level. Avoid general phrases.>"
}}

---

## HISTORICAL MONTHLY SALES DATA:
Use the following data for all predictions. DO NOT assume anything not seen in the numbers.

{json.dumps(monthly_history, indent=2)}
"""


    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    predictions = []

    for sku in variant_skus:
        variant = variant_lookup.get(sku)
        product = variant.product if variant and variant.product else None
        monthly_history = monthly_sales_to_list(monthly_sales_by_sku.get(sku, {}))

        prompt = build_prompt(sku, product.title if product else "Unknown Product", monthly_history)

        payload = {
    "model": "gpt-4o",  # ✅ Correct official model
    "messages": [
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.3,
    "max_tokens": 1000,
}


        try:
            response = requests.post(OPENAI_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
            # Extract the assistant's reply content
            choices = data.get("choices", [])
            if choices and "message" in choices[0] and "content" in choices[0]["message"]:
                gemini_text = choices[0]["message"]["content"].strip()
            else:
                gemini_text = "[No response text]"
            predictions.append({
                "variant_sku": sku,
                "product_title": product.title if product else None,
                "prediction_raw": gemini_text,
            })
        except Exception as e:
            predictions.append({
                "variant_sku": sku,
                "product_title": product.title if product else None,
                "prediction_raw": f"[OpenAI API Error] {str(e)}"
            })

        # Reduced delay - adjust as needed to avoid rate limiting
        time.sleep(0.6)

    result = []
    for sku in variant_skus:
        variant = variant_lookup.get(sku)
        product = variant.product if variant and variant.product else None
        result.append({
            "variant_sku": sku,
            "product_id": product.id if product else None,
            "product_shopify_id": product.shopify_id if product else None,
            "product_title": product.title if product else None,
            "variant_title": variant.title if variant else None,
            "price": variant.price if variant else None,
            "vendor": product.vendor if product else None,
            "product_type": product.product_type if product else None,
            "total_quantity_sold": total_qty_per_sku.get(sku, 0),
            "history": sales_data_by_sku.get(sku, []),
            "monthly_history": monthly_sales_to_list(monthly_sales_by_sku.get(sku, {})),
        })

    return JsonResponse({
        "openai_predictions": predictions,
    }, status=200)


# ----------------------------------------------------------
import os
import json
import requests
from collections import defaultdict
from datetime import datetime
from django.shortcuts import render
from django.utils.timezone import make_aware
from dotenv import load_dotenv

from .models import ProductVariant, OrderLineItem


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

    # Step 2: Build Prompt (latest improved version)
    def build_prompt(sku, title, history):
        return f"""
You are a domain-specific AI expert trained to predict fashion jewellery sales using statistical, trend-based, and behavioral data.

Your job is to analyze the **actual past sales history** of a fashion jewellery SKU and estimate **realistic, conservative** monthly sales quantities for the year 2024 in the Indian market — with a focus on *accuracy over optimism*.

---

### PRODUCT DETAILS:
- Product Name: "{title}"
- SKU: {sku}
- Today's Date: January 1, 2024
- Product Category: Fashion Jewellery (non-essential)
- Region: India

---

### STRICT MODELING RULES:
1. Use actual sales quantities and timestamps (below) to understand seasonality and demand.
2. If the product showed **declining sales** or **no sales in recent months**, assume demand is decreasing unless a strong seasonal pattern exists.
3. Only project increased sales in months where:
   - Past sales were high
   - Indian festivals or wedding seasons boost jewelry demand
   - Product has consistent monthly presence across multiple years
4. **DO NOT overestimate**. If 2023 sales are low or erratic, reduce 2024 predictions accordingly.
5. If past sales depended on **discounts**, and none are assumed in 2024, factor that drop.
6. Prioritize accuracy over completeness. It's okay to predict zero sales if trends suggest it.
7. Use reasoning like a demand forecaster: consider seasonality, saturation, and demand decay.
8. DO NOT assume a uniform year — each month must be estimated based on *actual past behavior* and *festive calendar*.

---

### INDIAN JEWELLERY SEASONALITY (Apply only when pattern supports it):
- Feb: Valentine’s Day (mild boost)
- Mar: Holi, Women’s Day
- Apr: Akshaya Tritiya (high potential)
- May: Wedding Season
- Aug: Raksha Bandhan, Onam
- Oct: Dussehra
- Nov: Diwali, Karwa Chauth
- Dec: Christmas + Winter weddings

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
(Use this as your only quantitative input for forecasting)
{json.dumps(history, indent=2)}
"""

    # Step 3: Call Gemini
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

    # Step 4: Actual sales for Jan–Dec 2024
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

    # Step 5: Build comparison table
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
