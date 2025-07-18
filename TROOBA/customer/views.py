import os
import requests
from django.utils.dateparse import parse_datetime
from django.shortcuts import HttpResponse ,render
from customer.models import ProductVariant
import requests
import google.generativeai as genai
from .models import ProductVariant
from dotenv import load_dotenv
import json
import re
from .models import OrderLineItem 
from django.db.models import Sum


from .models import (
    Location, CustomerProfile, ProductDetail, ProductImage, ProductOption,
    ProductOptionValue, ProductVariant, Order, OrderLineItem, Transaction,
    InventoryLog, LocalEvent, Collection, ProductCollection, Supplier, ProductSupplier
)

def fetch_and_store_shopify_data(request):
    store = os.getenv("SHOPIFY_STORE")
    api_version = os.getenv("SHOPIFY_API_VERSION", "2024-04")  # default version if not set
    access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")

    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Helper function to paginate through Shopify API responses
    def paginate(url):
        items = []
        while url:
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                raise Exception(f"Error fetching data from {url}: {resp.text}")
            data = resp.json()
            # Shopify paginates with 'link' header; parse if needed
            # For simplicity, here we assume page_info-based pagination:
            link_header = resp.headers.get('Link')
            url = None  # default: no next page
            if link_header:
                # Example: <https://...&page_info=abc>; rel="next"
                for part in link_header.split(','):
                    if 'rel="next"' in part:
                        url = part[part.find('<')+1:part.find('>')]
            items.extend(data.get(list(data.keys())[0], []))  # first key contains data array
        return items

    try:
        # 1. Fetch and Save Locations
        locations_url = f"https://{store}/admin/api/{api_version}/locations.json"
        locations = paginate(locations_url)
        for loc in locations:
            city = loc.get("city") or "Unknown City"
            state = loc.get("province") or "Unknown State"
            country = loc.get("country_name") or "Unknown Country"
            Location.objects.update_or_create(
                shopify_location_id=str(loc["id"]),
                defaults={
                    "city": city,
                    "state": state,
                    "country": country,
                    "region": None,
                    "cultural_traits": None,
                    "population_density": None,
                    "average_income": None,
                }
            )

        # 2. Fetch and Save Customers (paginated)
        customers_url = f"https://{store}/admin/api/{api_version}/customers.json?limit=250"
        customers = paginate(customers_url)
        for cust in customers:
            addr = cust.get("default_address", {})
            city = addr.get("city")
            state = addr.get("province")
            country = addr.get("country")
            location = None
            if city and state and country:
                location, _ = Location.objects.get_or_create(
                    city=city,
                    state=state,
                    country=country,
                    defaults={"shopify_location_id": None}
                )
            CustomerProfile.objects.update_or_create(
                shopify_customer_id=str(cust["id"]),
                defaults={
                    "first_name": cust.get("first_name"),
                    "last_name": cust.get("last_name"),
                    "email": cust.get("email"),
                    "phone": cust.get("phone"),
                    "location": location,
                    "gender": None,
                    "age_range": None,
                    "purchase_style": None,
                    "accepts_marketing": cust.get("accepts_marketing", False),
                    "total_orders_count": cust.get("orders_count", 0),
                    "total_spent": float(cust.get("total_spent") or 0.00),
                    "created_at": parse_datetime(cust.get("created_at")),
                    "updated_at": parse_datetime(cust.get("updated_at")),
                }
            )

        # 3. Fetch and Save Products (paginated)
        products_url = f"https://{store}/admin/api/{api_version}/products.json?limit=250"
        products = paginate(products_url)
        for product in products:
            created_at = parse_datetime(product.get("created_at"))
            updated_at = parse_datetime(product.get("updated_at"))
            published_at = parse_datetime(product.get("published_at")) if product.get("published_at") else None

            prod_obj, _ = ProductDetail.objects.update_or_create(
                shopify_product_id=str(product["id"]),
                defaults={
                    "title": product.get("title", "No Title"),
                    "handle": product.get("handle"),
                    "vendor": product.get("vendor", ""),
                    "product_type": product.get("product_type", ""),
                    "status": product.get("status", ""),
                    "tags": product.get("tags", ""),
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "published_at": published_at,
                }
            )

            # Save Product Images
            for img in product.get("images", []):
                ProductImage.objects.update_or_create(
                    shopify_image_id=str(img["id"]),
                    defaults={
                        "product": prod_obj,
                        "src": img.get("src"),
                        "alt": img.get("alt"),
                        "position": img.get("position"),
                        "variant_ids": None,
                    }
                )

            # Save Product Options and Option Values
            for opt in product.get("options", []):
                opt_obj, _ = ProductOption.objects.update_or_create(
                    product=prod_obj,
                    shopify_option_id=str(opt.get("id") or ""),
                    defaults={
                        "name": opt.get("name"),
                        "position": opt.get("position", 0),
                    }
                )
                # Shopify returns option values in 'values' list
                for idx, val in enumerate(opt.get("values", [])):
                    ProductOptionValue.objects.update_or_create(
                        option=opt_obj,
                        value=val,
                        defaults={
                            "position": idx + 1,
                        }
                    )

            # Save Product Variants
            for variant in product.get("variants", []):
                ProductVariant.objects.update_or_create(
                    shopify_variant_id=str(variant["id"]),
                    defaults={
                        "product": prod_obj,
                        "title": variant.get("title", ""),
                        "sku": variant.get("sku") or None,
                        "price": float(variant.get("price") or 0.00),
                        "cost_price": float(variant.get("cost") or 0.00) if variant.get("cost") else None,
                        "compare_at_price": float(variant.get("compare_at_price") or 0.00) if variant.get("compare_at_price") else None,
                        "weight_grams": float(variant.get("weight") or 0.0) if variant.get("weight") else None,
                        "inventory_quantity": variant.get("inventory_quantity") or 0,
                        "inventory_management": variant.get("inventory_management"),
                        "metal_type": None,
                        "karat": None,
                        "stone_type": None,
                        "option1": variant.get("option1"),
                        "option2": variant.get("option2"),
                        "option3": variant.get("option3"),
                        "created_at": parse_datetime(variant.get("created_at")),
                        "updated_at": parse_datetime(variant.get("updated_at")),
                    }
                )

        # --- You can similarly add fetch/save for Orders, Transactions, Collections, Suppliers, etc. ---

    except Exception as e:
        return HttpResponse(f"<h1>Error during sync: {str(e)}</h1>", status=500)

    return HttpResponse(
        f"<h1>Synced: {len(locations)} locations, {len(customers)} customers, {len(products)} products successfully.</h1>"
    )



load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def sales_predictions(request):
    variants = ProductVariant.objects.all()

    # 1. Get historical sales per variant (sum of quantity sold)
    sales_data = (
        OrderLineItem.objects
        .values('variant__shopify_variant_id', 'variant__title')
        .annotate(total_sold=Sum('quantity'))
    )

    # Build a lookup dictionary for quick access: variant_id -> total_sold
    sales_lookup = {
        item['variant__shopify_variant_id']: item['total_sold'] or 0 for item in sales_data
    }

    # 2. Prepare input prompt for Gemini using historical sales ONLY (no inventory in sales prediction)
    prompt_lines = []
    for v in variants:
        historical_sales = sales_lookup.get(v.shopify_variant_id, 0)
        prompt_lines.append(f"Item: {v.title}, Past Sales: {historical_sales}")

    prompt_text = "\n".join(prompt_lines)
    full_prompt = (
        "You are an AI sales forecasting assistant.\n"
        "Based on the past sales data below, predict the expected sales "
        "quantity for each item in the next 2 weeks. Respond strictly in JSON list format:\n"
        '[{"item_name": "Item A", "predicted_sales": 30}, ...]\n\n' +
        prompt_text
    )

    # 3. Call Gemini
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        response = model.generate_content(full_prompt)
        raw_text = response.text.strip()

        # Clean triple backticks and json tags if any
        match = re.search(r"```json(.*?)```", raw_text, re.DOTALL)
        if match:
            raw_text = match.group(1).strip()

        print("Cleaned Gemini response:", raw_text)

        gemini_predictions = json.loads(raw_text)
    except Exception as e:
        print("Gemini error:", e)
        gemini_predictions = []

    # 4. Map predictions for quick lookup
    predicted_sales_dict = {}
    for entry in gemini_predictions:
        item_name = entry.get("item_name")
        predicted = entry.get("predicted_sales", 0)
        if item_name:
            predicted_sales_dict[item_name] = predicted

    # 5. Prepare table data with predicted sales and 'more_required'
    table_data = []
    for v in variants:
        predicted = predicted_sales_dict.get(v.title, 0)
        more_required = predicted - v.inventory_quantity
        if more_required > 0:
            more_required_display = f"+{more_required}"
        elif more_required < 0:
            more_required_display = f"{more_required}"
        else:
            more_required_display = "0"

        table_data.append({
            'item_name': v.title,
            'inventory_quantity': v.inventory_quantity,
            'predicted_sales': predicted,
            'more_required': more_required_display,
        })

    return render(request, 'customer/sales_predictions.html', {'table_data': table_data})