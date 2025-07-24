from django.urls import path
from .views import fetch_and_store_all ,  top_20_selling_products_till_2024_view ,top_20_selling_products_2024_onward_view


urlpatterns = [
    path('fetch-shopify/', fetch_and_store_all, name='fetch_shopify'),
    path('top-products-till-2024/', top_20_selling_products_till_2024_view, name='top_products_till_2024'),
    path('top-products-from-2024/', top_20_selling_products_2024_onward_view, name='top_products_2024'),
]
