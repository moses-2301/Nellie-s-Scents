from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('shop/', views.shop, name='shop'),
    path('contact/', views.contact, name='contact'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    
    # Authentication
    path('signup/', views.signup_request, name='signup'),
    path('signup/verify/', views.signup_verify, name='signup_verify'),
    path('signup/resend-otp/', views.resend_signup_otp, name='resend_signup_otp'),
    path('social/<str:provider>/', views.social_redirect, name='social_redirect'),
    path('password-reset/', views.forgot_password_request, name='forgot_password'),
    path('password-reset/verify/', views.forgot_password_verify, name='forgot_password_verify'),
    path('otp/request/', views.otp_request, name='otp_request'),
    path('otp/verify/', views.otp_verify, name='otp_verify'),
    path('otp/success/', views.otp_success, name='otp_success'),
    path('logout/', views.logout_user, name='logout'),
    
    # Products
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # Cart
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/data/', views.get_cart_data, name='get_cart_data'),
    
    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/success/<int:order_id>/', views.checkout_success, name='checkout_success'),
    
    # Payment
    path('payment/initiate/<int:order_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment/verify/<int:order_id>/', views.verify_payment, name='verify_payment'),

    # Dashboard analytics API
    path('dashboard/api/summary/', views.dashboard_summary, name='dashboard_summary'),
    path('dashboard/api/orders-per-day/', views.dashboard_orders_per_day, name='dashboard_orders_per_day'),
    path('dashboard/api/revenue-per-day/', views.dashboard_revenue_per_day, name='dashboard_revenue_per_day'),
    path('dashboard/api/category-revenue/', views.dashboard_category_revenue, name='dashboard_category_revenue'),
    path('dashboard/api/top-products/', views.dashboard_top_products, name='dashboard_top_products'),

    # Admin undo
    path('admin/undo/', views.undo_admin_change, name='undo_admin_change'),
]
