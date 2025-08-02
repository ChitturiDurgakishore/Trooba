
import os
import requests
from dotenv import load_dotenv
from django.utils.dateparse import parse_datetime
from customer.models import ProductVariant

# Load environment variables
load_dotenv()

SHOP_NAME = 'tarinika'
API_VERSION = '2025-04'
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

def update_created_at_from_shopify():
    if not ACCESS_TOKEN:
        print("❌ Access token not found. Make sure it's set in .env.")
        return

    variants = ProductVariant.objects.exclude(sku__isnull=True).exclude(sku='')

    for variant in variants:
        sku = variant.sku
        url = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/variants.json?sku={sku}"
        headers = {
            "X-Shopify-Access-Token": ACCESS_TOKEN,
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                shopify_variants = data.get("variants", [])
                if shopify_variants:
                    created_at_str = shopify_variants[0].get("created_at")
                    if created_at_str:
                        variant.created_at = parse_datetime(created_at_str)
                        variant.save()
                        print(f"✅ Updated {sku} -> created_at = {created_at_str}")
                    else:
                        print(f"⚠️ created_at missing for {sku}")
                else:
                    print(f"❌ No Shopify variant found for {sku}")
            else:
                print(f"❌ Request failed for {sku} - Status: {response.status_code}")
        except Exception as e:
            print(f"💥 Error fetching {sku}: {e}")
