from django.urls import path
from .views import fetch_and_store_all ,  top_20_selling_products_till_2024_view 
# ,top_20_selling_products_2024_onward_view
from .views import compare_sku_prediction_view,sku_sales_history 
from .views import Fetching_items,generate_prompt_view


urlpatterns = [
    path('fetch-shopify/', fetch_and_store_all, name='fetch_shopify'),
    path('', top_20_selling_products_till_2024_view, name='top_products_till_2024'),
    # path('top-products-from-2024/', top_20_selling_products_2024_onward_view, name='top_products_2024'),
    path("sku-history/<str:sku>/", sku_sales_history, name="sku_sales_history"),
    path('compare/<str:sku>/', compare_sku_prediction_view, name='compare_sku'),
    # path('predict-2024-sales/', fetch_historical_sales_till_2024, name='predict_2024_sales'),
    path("top-items/", Fetching_items, name="Fetching"),
    path('generate-prompt/', generate_prompt_view, name='generate_prompt'),

 ]
