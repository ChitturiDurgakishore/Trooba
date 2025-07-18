from django.urls import path
from .views import fetch_and_store_shopify_data , sales_predictions

urlpatterns = [
    path('fetch-shopify-data/', fetch_and_store_shopify_data, name='fetch_shopify_data'),
    path('sales-predictions/', sales_predictions, name='sales_predictions'),
]
