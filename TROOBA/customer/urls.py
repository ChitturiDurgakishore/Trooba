from django.urls import path
from .views import fetch_and_store_all ,  top_20_selling_products_till_2024_view ,top_20_selling_products_2024_onward_view,fetch_historical_sales_till_2024,test_gemini_api
from .views import compare_sku_prediction_view,sku_sales_history
urlpatterns = [
    path('fetch-shopify/', fetch_and_store_all, name='fetch_shopify'),
    path('top-products-till-2024/', top_20_selling_products_till_2024_view, name='top_products_till_2024'),
    path('top-products-from-2024/', top_20_selling_products_2024_onward_view, name='top_products_2024'),
    path('predict-2024-sales/', fetch_historical_sales_till_2024, name='predict_2024_sales'),
    path('testing/',test_gemini_api),
    path('compare/<str:sku>/', compare_sku_prediction_view, name='compare_sku'),
    path("sku-history/<str:sku>/",sku_sales_history, name="sku_sales_history"),
]
