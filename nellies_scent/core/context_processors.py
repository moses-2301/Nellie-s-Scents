from decimal import Decimal
from .models import Product, ContactMessage, Order, CartItem
from django.contrib.auth.models import User


def cart_sidebar(request):
    cart_sidebar_items = []
    cart_sidebar_subtotal = Decimal('0')
    cart_sidebar_count = 0

    try:
        if request.user.is_authenticated:
            # Logged-in: read from database
            db_items = CartItem.objects.filter(
                user=request.user
            ).select_related('product')

            for item in db_items:
                item_total = item.product.price * item.quantity
                cart_sidebar_subtotal += item_total
                cart_sidebar_count += item.quantity
                cart_sidebar_items.append({
                    'cart_key': f"{item.product.id}_{item.size}",  # ← added
                    'name': item.product.name,
                    'image': item.product.image.url if item.product.image else '',
                    'size': item.size,
                    'quantity': item.quantity,
                    'price': item.product.price,
                    'total': item_total,
                    'product_url': item.product.get_absolute_url(),
                })

        else:
            # Anonymous: read from session
            cart = request.session.get('cart', {})
            for cart_key, item in cart.items():  # ← unpacked cart_key from loop
                try:
                    product = Product.objects.get(id=item['product_id'])
                except Product.DoesNotExist:
                    continue

                quantity = int(item.get('quantity', 0))
                price = Decimal(item.get('price', '0'))
                item_total = price * quantity
                cart_sidebar_subtotal += item_total
                cart_sidebar_count += quantity
                cart_sidebar_items.append({
                    'cart_key': cart_key,  # ← added
                    'name': product.name,
                    'image': product.image.url if product.image else '',
                    'size': item.get('size', ''),
                    'quantity': quantity,
                    'price': price,
                    'total': item_total,
                    'product_url': product.get_absolute_url(),
                })

    except Exception:
        pass  # Never crash the page over a sidebar

    return {
        'cart_sidebar_items': cart_sidebar_items,
        'cart_sidebar_subtotal': cart_sidebar_subtotal,
        'cart_sidebar_count': cart_sidebar_count,
    }


def admin_context(request):
    """Context processor for admin dashboard - provides unread messages and pending orders"""
    if request.user.is_authenticated and request.user.is_superuser:
        unread_messages = ContactMessage.objects.filter(is_read=False).count()
        pending_orders = Order.objects.filter(status='pending').count()
        total_products = Product.objects.count()
        total_users = User.objects.count()

        return {
            'unread_messages': unread_messages,
            'pending_orders': pending_orders,
            'total_products': total_products,
            'total_users': total_users,
        }
    return {}