from django.urls import path, include
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('overview/', views.overview, name='overview'),

    path('products/', views.products, name='products'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:product_id>/', views.product_edit, name='product_edit'),
    path('products/<int:product_id>/delete/', views.product_delete, name='product_delete'),

    path('orders/', views.orders, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),

    path('messages/', views.messages_list, name='messages'),
    path('messages/<int:message_id>/', views.message_detail, name='message_detail'),

    path('analytics/', views.analytics, name='analytics'),

    path('users/', views.users, name='users'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),

    path('accounts/', views.accounts, name='accounts'),
    path('auth/', views.auth_management, name='auth_management'),
    path('sites/', views.sites_management, name='sites_management'),
    
    # Social Apps CRUD
    path('socialapps/', views.socialapp_list, name='socialapp_list'),
    path('socialapps/create/', views.socialapp_create, name='socialapp_create'),
    path('socialapps/<int:app_id>/edit/', views.socialapp_edit, name='socialapp_edit'),
    path('socialapps/<int:app_id>/delete/', views.socialapp_delete, name='socialapp_delete'),
    
    # Connected Accounts & Tokens (read-only)
    path('social/', views.social_accounts, name='social_accounts'),
    path('social/accounts/<int:account_id>/disconnect/', views.social_account_disconnect, name='social_account_disconnect'),
    path('social/tokens/<int:token_id>/revoke/', views.social_token_revoke, name='social_token_revoke'),
    
    path('core/', views.core_overview, name='core_overview'),
    path('api/social/', include('dashboard.api_urls')),
    path('api/summary/', views.api_summary, name='api_summary'),
    path('api/orders-per-day/', views.api_orders_per_day, name='api_orders_per_day'),
    path('api/revenue-per-day/', views.api_revenue_per_day, name='api_revenue_per_day'),
    path('api/top-products/', views.api_top_products, name='api_top_products'),
]
