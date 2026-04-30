import json
import urllib.request
import urllib.error
from datetime import timedelta
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, F, DecimalField, Q
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken

from core.models import Product, Order, OrderItem, ContactMessage
from .forms import ProductForm, OrderStatusForm, SiteForm, UserForm, SocialAppForm
from .provider_utils import get_provider_display


def dashboard_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/accounts/login/?next=' + request.path)
        if not request.user.is_superuser:
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return wrapper


@dashboard_required
def welcome(request):
    return render(request, 'dashboard/welcome.html', {
        'admin_name': request.user.first_name or request.user.username,
    })


@dashboard_required
def overview(request):
    today = timezone.localtime(timezone.now()).date()
    current_month_start = today.replace(day=1)

    total_revenue = OrderItem.objects.filter(order__status='confirmed')
    total_revenue = total_revenue.aggregate(total=Sum(F('price') * F('quantity'), output_field=DecimalField()))['total'] or 0

    month_revenue = OrderItem.objects.filter(order__status='confirmed', order__created_at__date__gte=current_month_start, order__created_at__date__lte=today)
    month_revenue = month_revenue.aggregate(total=Sum(F('price') * F('quantity'), output_field=DecimalField()))['total'] or 0

    pending_orders = Order.objects.filter(status='pending').count()
    unread_messages = ContactMessage.objects.filter(is_read=False).count()
    total_products = Product.objects.count()

    return render(request, 'dashboard/overview.html', {
        'total_revenue': float(total_revenue),
        'month_revenue': float(month_revenue),
        'pending_orders': pending_orders,
        'unread_messages': unread_messages,
        'total_products': total_products,
    })


@dashboard_required
def products(request):
    products_queryset = Product.objects.order_by('-created_at')
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')

    if search_query:
        products_queryset = products_queryset.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))
    if category_filter:
        products_queryset = products_queryset.filter(category=category_filter)

    return render(request, 'dashboard/products.html', {
        'products': products_queryset,
        'categories': Product.CATEGORY_CHOICES,
        'search_query': search_query,
        'category_filter': category_filter,
    })


@dashboard_required
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard:products')
    return render(request, 'dashboard/product_form.html', {'form': form, 'page_title': 'Add Product'})


@dashboard_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard:products')
    return render(request, 'dashboard/product_form.html', {'form': form, 'product': product, 'page_title': 'Edit Product'})


@dashboard_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
        return redirect('dashboard:products')
    return render(request, 'dashboard/product_delete.html', {'product': product})


@dashboard_required
def orders(request):
    orders_queryset = Order.objects.order_by('-created_at')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    if status_filter:
        orders_queryset = orders_queryset.filter(status=status_filter)
    if search_query:
        orders_queryset = orders_queryset.filter(
            Q(full_name__icontains=search_query) | Q(phone__icontains=search_query) | Q(id__icontains=search_query)
        )
    return render(request, 'dashboard/orders.html', {
        'orders': orders_queryset,
        'statuses': Order.STATUS_CHOICES,
        'status_filter': status_filter,
        'search_query': search_query,
    })


def _broadcast_realtime_event(event_type, payload=None):
    payload = payload or {}
    data = json.dumps({'type': event_type, 'payload': payload}).encode('utf-8')
    request = urllib.request.Request(
        'http://localhost:3001/event',
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        urllib.request.urlopen(request, timeout=2)
    except urllib.error.URLError:
        pass


@dashboard_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.orderitem_set.all()
    original_status = order.status
    form = OrderStatusForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        form.save()
        if original_status != order.status and order.status == 'completed':
            _broadcast_realtime_event('order_confirmed', {'order_id': order.id})
        return redirect('dashboard:order_detail', order_id=order.id)
    return render(request, 'dashboard/order_detail.html', {'order': order, 'items': items, 'form': form})


@dashboard_required
def messages_list(request):
    messages_queryset = ContactMessage.objects.order_by('-created_at')
    unread_only = request.GET.get('unread', '')
    if unread_only:
        messages_queryset = messages_queryset.filter(is_read=False)
    if request.method == 'POST':
        message_id = request.POST.get('message_id')
        message = get_object_or_404(ContactMessage, id=message_id)
        message.is_read = True
        message.save()
        return redirect('dashboard:messages')
    return render(request, 'dashboard/messages.html', {
        'messages': messages_queryset,
        'unread_count': ContactMessage.objects.filter(is_read=False).count(),
    })


@dashboard_required
def message_detail(request, message_id):
    message = get_object_or_404(ContactMessage, id=message_id)
    if not message.is_read:
        message.is_read = True
        message.save()
    return render(request, 'dashboard/message_detail.html', {'message': message})


@dashboard_required
def analytics(request):
    return render(request, 'dashboard/analytics.html', {})


@dashboard_required
def users(request):
    users_queryset = User.objects.order_by('-date_joined')
    search_query = request.GET.get('q', '')
    if search_query:
        users_queryset = users_queryset.filter(Q(username__icontains=search_query) | Q(email__icontains=search_query) | Q(first_name__icontains=search_query))
    return render(request, 'dashboard/users.html', {
        'users': users_queryset,
        'search_query': search_query,
    })


@dashboard_required
def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user_orders = Order.objects.filter(user=user)
    form = UserForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard:user_detail', user_id=user.id)
    return render(request, 'dashboard/user_detail.html', {'user': user, 'user_orders': user_orders, 'form': form})


@dashboard_required
def user_create(request):
    form = UserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard:users')
    return render(request, 'dashboard/user_form.html', {'form': form, 'page_title': 'Create User'})


@dashboard_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        return redirect('dashboard:users')
    return render(request, 'dashboard/user_delete.html', {'user': user})


@dashboard_required
def accounts(request):
    linked_accounts = SocialAccount.objects.filter(user=request.user)
    return render(request, 'dashboard/accounts.html', {'linked_accounts': linked_accounts})


@dashboard_required
def auth_management(request):
    users_queryset = User.objects.order_by('-date_joined')
    return render(request, 'dashboard/auth.html', {'users': users_queryset})


@dashboard_required
def sites_management(request):
    site = Site.objects.first()
    form = SiteForm(request.POST or None, instance=site)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard:sites_management')
    return render(request, 'dashboard/sites.html', {'form': form, 'site': site})


@dashboard_required
def socialapp_list(request):
    """List all configured social apps."""
    apps = SocialApp.objects.prefetch_related('sites').order_by('provider')
    search = request.GET.get('q', '').strip()
    if search:
        apps = apps.filter(Q(provider__icontains=search) | Q(name__icontains=search))
    
    return render(request, 'dashboard/socialapp_list.html', {
        'apps': apps,
        'search': search,
    })


@dashboard_required
def socialapp_create(request):
    """Create a new social app."""
    if request.method == 'POST':
        form = SocialAppForm(request.POST)
        if form.is_valid():
            app = form.save()
            provider_name = get_provider_display(app.provider)
            messages.success(request, f'Social app for {provider_name} created successfully.')
            return redirect('dashboard:socialapp_list')
    else:
        form = SocialAppForm()
    
    return render(request, 'dashboard/socialapp_form.html', {
        'form': form,
        'page_title': 'Create Social App',
        'action': 'Create',
    })


@dashboard_required
def socialapp_edit(request, app_id):
    """Edit an existing social app."""
    app = get_object_or_404(SocialApp, id=app_id)
    
    if request.method == 'POST':
        form = SocialAppForm(request.POST, instance=app)
        if form.is_valid():
            form.save()
            provider_name = get_provider_display(app.provider)
            messages.success(request, f'{provider_name} app updated successfully.')
            return redirect('dashboard:socialapp_list')
    else:
        form = SocialAppForm(instance=app)
    
    provider_name = get_provider_display(app.provider)
    return render(request, 'dashboard/socialapp_form.html', {
        'form': form,
        'app': app,
        'page_title': f'Edit {provider_name} App',
        'action': 'Update',
    })


@dashboard_required
def socialapp_delete(request, app_id):
    """Delete a social app."""
    app = get_object_or_404(SocialApp, id=app_id)
    
    if request.method == 'POST':
        provider_name = get_provider_display(app.provider)
        app.delete()
        messages.success(request, f'{provider_name} app deleted successfully.')
        return redirect('dashboard:socialapp_list')
    
    return render(request, 'dashboard/socialapp_delete.html', {'app': app})


@dashboard_required
def social_accounts(request):
    """View for managing all linked social accounts and tokens (read-only)."""
    provider_filter = request.GET.get('provider', '').strip()
    account_search = request.GET.get('q', '').strip()

    accounts = SocialAccount.objects.select_related('user').order_by('-date_joined')
    if provider_filter:
        accounts = accounts.filter(provider=provider_filter)
    if account_search:
        accounts = accounts.filter(Q(user__username__icontains=account_search) | Q(uid__icontains=account_search))

    tokens = SocialToken.objects.select_related('account', 'account__user').order_by('-id')
    if provider_filter:
        tokens = tokens.filter(account__provider=provider_filter)

    total_accounts = accounts.count()
    total_tokens = tokens.count()

    return render(request, 'dashboard/social_accounts.html', {
        'accounts': accounts,
        'tokens': tokens,
        'provider_filter': provider_filter,
        'account_search': account_search,
        'total_accounts': total_accounts,
        'total_tokens': total_tokens,
    })


@dashboard_required
def social_account_disconnect(request, account_id):
    """Disconnect a user's linked social account."""
    account = get_object_or_404(SocialAccount, id=account_id)
    if request.method == 'POST':
        account.delete()
        messages.success(request, f'Social account for {account.user.username} disconnected.')
    return redirect('dashboard:social_accounts')


@dashboard_required
def social_token_revoke(request, token_id):
    """Revoke a stored social token."""
    token = get_object_or_404(SocialToken, id=token_id)
    if request.method == 'POST':
        token.delete()
        messages.success(request, 'Social token revoked.')
    return redirect('dashboard:social_accounts')


@dashboard_required
def core_overview(request):
    return render(request, 'dashboard/core.html', {
        'total_products': Product.objects.count(),
        'total_orders': Order.objects.count(),
        'total_messages': ContactMessage.objects.count(),
    })


def _api_date_range(request):
    days = int(request.GET.get('days', 30))
    today = timezone.localtime(timezone.now()).date()
    return today - timedelta(days=days - 1), today


@dashboard_required
def api_summary(request):
    start_date, end_date = _api_date_range(request)
    total_revenue = OrderItem.objects.filter(order__status='confirmed', order__created_at__date__gte=start_date, order__created_at__date__lte=end_date)
    total_revenue = total_revenue.aggregate(total=Sum(F('price') * F('quantity'), output_field=DecimalField()))['total'] or 0
    return JsonResponse({'total_revenue': float(total_revenue)})


@dashboard_required
def api_orders_per_day(request):
    start_date, end_date = _api_date_range(request)
    data = Order.objects.filter(status='confirmed', created_at__date__gte=start_date, created_at__date__lte=end_date)
    labels = []
    values = []
    for day in range((end_date - start_date).days + 1):
        date = start_date + timezone.timedelta(days=day)
        labels.append(date.strftime('%b %d'))
        values.append(data.filter(created_at__date=date).count())
    return JsonResponse({'labels': labels, 'data': values})


@dashboard_required
def api_revenue_per_day(request):
    start_date, end_date = _api_date_range(request)
    entries = OrderItem.objects.filter(order__status='confirmed', order__created_at__date__gte=start_date, order__created_at__date__lte=end_date)
    labels = []
    values = []
    for day in range((end_date - start_date).days + 1):
        date = start_date + timezone.timedelta(days=day)
        labels.append(date.strftime('%b %d'))
        values.append(float(entries.filter(order__created_at__date=date).aggregate(total=Sum(F('price') * F('quantity'), output_field=DecimalField()))['total'] or 0))
    return JsonResponse({'labels': labels, 'data': values})


@dashboard_required
def api_top_products(request):
    start_date, end_date = _api_date_range(request)
    data = OrderItem.objects.filter(order__status='confirmed', order__created_at__date__gte=start_date, order__created_at__date__lte=end_date)
    grouped = data.values('product__name').annotate(quantity=Sum('quantity')).order_by('-quantity')[:10]
    return JsonResponse({
        'labels': [item['product__name'] for item in grouped],
        'data': [item['quantity'] for item in grouped]
    })
