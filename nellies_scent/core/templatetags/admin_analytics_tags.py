from django import template
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
from ..models import Order, Product, ContactMessage

register = template.Library()


def _today_period():
    today = timezone.now().date()
    start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    return start, end


@register.simple_tag
def admin_orders_today():
    start, end = _today_period()
    return Order.objects.filter(status='confirmed', created_at__range=(start, end)).count()


@register.simple_tag
def admin_revenue_today():
    start, end = _today_period()
    revenue = Decimal('0')
    for order in Order.objects.filter(status='completed', created_at__range=(start, end)):
        revenue += order.get_total()
    return f"₦{revenue:,.2f}"


@register.simple_tag
def admin_revenue_overall():
    revenue = Decimal('0')
    for order in Order.objects.filter(status='completed'):
        revenue += order.get_total()
    return f"₦{revenue:,.2f}"


@register.simple_tag
def admin_total_revenue():
    return admin_revenue_overall()


@register.simple_tag
def admin_total_products():
    return Product.objects.count()


@register.simple_tag
def admin_unread_messages():
    return ContactMessage.objects.filter(is_read=False).count()


@register.simple_tag
def admin_total_orders():
    return Order.objects.count()


@register.simple_tag
def admin_active_users():
    return User.objects.count()


@register.simple_tag
def admin_conversion_rate():
    total_orders = Order.objects.count()
    if total_orders == 0:
        return "0%"
    confirmed_orders = Order.objects.filter(status='completed').count()
    return f"{round((confirmed_orders / total_orders) * 100, 2)}%"
