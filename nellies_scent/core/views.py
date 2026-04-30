from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q, Count, Sum, F, DecimalField
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.conf import settings
from django.core.mail import send_mail
from django.db.models.functions import TruncDate
import json
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from .models import Product, ContactMessage, Order, OrderItem, Review, EmailOTP, CartItem, UndoData
from .forms import ContactForm, CheckoutForm, SearchForm, ReviewForm, SignupForm, SignupOTPForm, PasswordResetRequestForm, PasswordResetOTPForm, OTPRequestForm, OTPVerifyForm, CustomLoginForm


def _get_cart_from_session(request):
    """Get cart from session"""
    if 'cart' not in request.session:
        request.session['cart'] = {}
    return request.session['cart']


def _save_cart_to_session(request, cart):
    """Save cart to session and mark as modified"""
    request.session['cart'] = cart
    request.session.modified = True


def _merge_session_cart_with_user_cart(request, user):
    """Merge session cart items with user's database cart"""
    session_cart = _get_cart_from_session(request)
    
    if not session_cart:
        # Load user's cart from database to session
        user_cart_items = CartItem.objects.filter(user=user).select_related('product')
        for cart_item in user_cart_items:
            cart_key = f"{cart_item.product.id}_{cart_item.size}"
            session_cart[cart_key] = {
                'product_id': cart_item.product.id,
                'name': cart_item.product.name,
                'price': str(cart_item.product.price),
                'size': cart_item.size,
                'quantity': cart_item.quantity,
                'image': cart_item.product.image.url if cart_item.product.image else ''
            }
        _save_cart_to_session(request, session_cart)
        return
    
    # Merge session cart with database cart
    for cart_key, item in session_cart.items():
        product_id = item['product_id']
        size = item['size']
        quantity = item['quantity']
        
        # Check if item already exists in user's database cart
        existing_item = CartItem.objects.filter(
            user=user,
            product_id=product_id,
            size=size
        ).first()
        
        if existing_item:
            # Update quantity
            existing_item.quantity += quantity
            existing_item.save()
        else:
            # Create new cart item
            CartItem.objects.create(
                user=user,
                product_id=product_id,
                size=size,
                quantity=quantity
            )
    
    # Clear session cart after merging
    request.session['cart'] = {}
    request.session.modified = True


def _generate_otp_code(length=6):
    return ''.join(random.choices(string.digits, k=length))


def _send_otp_email(email, purpose, code):
    subject = "Nellie's Scent OTP Verification"
    if purpose == 'signup':
        message = (
            f"Your signup verification code is {code}. "
            "Enter this code on the Nellie's Scent signup page to complete account creation. "
            "This code expires in 10 minutes."
        )
    else:
        message = (
            f"Your password reset code is {code}. "
            "Enter this code on the Nellie's Scent password reset page to continue. "
            "This code expires in 10 minutes."
        )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )


def _verify_otp(email, code, purpose):
    expiry = timezone.now() - timedelta(minutes=10)
    otp = EmailOTP.objects.filter(
        email=email,
        purpose=purpose,
        code=code,
        verified=False,
        created_at__gte=expiry
    ).order_by('-created_at').first()
    if otp:
        otp.verified = True
        otp.save()
        return True
    return False


def get_cart_count(request):
    """Get total items in cart"""
    if request.user.is_authenticated:
        # Count from database
        return CartItem.objects.filter(user=request.user).aggregate(
            total=Sum('quantity')
        )['total'] or 0
    else:
        # Count from session
        cart = _get_cart_from_session(request)
        return sum(int(item['quantity']) for item in cart.values())


def get_cart_items_with_products(request):
    """Get cart items with product objects"""
    if request.user.is_authenticated:
        # Get from database
        cart_items_db = CartItem.objects.filter(user=request.user).select_related('product')
        cart_items = []
        for item in cart_items_db:
            cart_items.append({
                'cart_key': f"{item.product.id}_{item.size}",
                'product': item.product,
                'size': item.size,
                'quantity': item.quantity,
                'get_total_ngn': item.get_total_ngn()
            })
        return cart_items
    else:
        # Get from session
        cart = _get_cart_from_session(request)
        cart_items = []
        
        for cart_key, item in cart.items():
            product = Product.objects.get(id=item['product_id'])
            cart_items.append({
                'cart_key': cart_key,
                'product': product,
                'size': item['size'],
                'quantity': item['quantity'],
                'get_total_ngn': f"₦{Decimal(item['price']) * item['quantity']:,.2f}"
            })
        
        return cart_items


def index(request):
    featured_products = []
    for category_key, _ in Product.CATEGORY_CHOICES:
        product = Product.objects.filter(category=category_key).order_by('-created_at').first()
        if product:
            featured_products.append(product)
        if len(featured_products) == 3:
            break

    if len(featured_products) < 3:
        existing_ids = [p.id for p in featured_products]
        additional = Product.objects.exclude(id__in=existing_ids).order_by('-created_at')[:3 - len(featured_products)]
        featured_products.extend(additional)

    slideshow_products = list(Product.objects.filter(image__isnull=False).order_by('?')[:3])
    if len(slideshow_products) < 3:
        existing_ids = [p.id for p in slideshow_products]
        additional = Product.objects.filter(image__isnull=False).exclude(id__in=existing_ids).order_by('-created_at')[:3 - len(slideshow_products)]
        slideshow_products.extend(additional)

    cart_count = get_cart_count(request)
    return render(request, 'core/index.html', {
        'featured_products': featured_products,
        'slideshow_products': slideshow_products,
        'cart_count': cart_count
    })


def about(request):
    cart_count = get_cart_count(request)
    return render(request, 'core/about.html', {'cart_count': cart_count})


def signup_request(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']

            if User.objects.filter(email=email).exists():
                form.add_error('email', 'An account already exists with this email.')
            elif User.objects.filter(username=username).exists():
                form.add_error('username', 'This username is already taken.')
            else:
                otp_code = _generate_otp_code()
                EmailOTP.objects.create(email=email, code=otp_code, purpose='signup')
                request.session['signup_data'] = {
                    'email': email,
                    'username': username,
                    'password': password,
                }
                _send_otp_email(email, 'signup', otp_code)
                return redirect('core:signup_verify')
    else:
        form = SignupForm()

    return render(request, 'account/signup.html', {
        'form': form,
        'cart_count': get_cart_count(request),
    })


def signup_verify(request):
    signup_data = request.session.get('signup_data')

    if not signup_data:
        return redirect('core:signup')

    error_message = None

    if request.method == 'POST':
        form = SignupOTPForm(request.POST)

        if form.is_valid():
            code = form.cleaned_data['code']

            if _verify_otp(signup_data['email'], code, 'signup'):
                user = User.objects.create_user(
                    username=signup_data['username'],
                    email=signup_data['email'],
                    password=signup_data['password']
                )

                # Create profile with verified status
                from .models import Profile
                Profile.objects.create(
                    user=user,
                    is_verified=True
                )

                # FIX: specify authentication backend
                auth_login(
                    request,
                    user,
                    backend='django.contrib.auth.backends.ModelBackend'
                )

                messages.success(
                    request,
                    "You have successfully signed up"
                )

                request.session.pop('signup_data', None)

                return redirect('core:index')

            error_message = "The OTP code is invalid or expired. Please request a new code."

    else:
        form = SignupOTPForm()

    return render(request, 'account/signup_verify_otp.html', {
        'form': form,
        'error_message': error_message,
        'cart_count': get_cart_count(request),
    })


def resend_signup_otp(request):
    """
    Resend OTP for signup verification.
    
    Requires 'signup_data' in session and limits to 5 resend attempts.
    Returns JSON response.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)

    signup_data = request.session.get('signup_data')
    
    if not signup_data:
        return JsonResponse({'status': 'error', 'message': 'Session expired. Please sign up again.'}, status=400)

    # Check resend count in session
    otp_resend_count = request.session.get('otp_resend_count', 0)
    
    if otp_resend_count >= 5:
        return JsonResponse({
            'status': 'error',
            'message': 'You have reached the maximum OTP resend limit. Please contact support.'
        }, status=429)

    try:
        # Generate new OTP
        otp_code = _generate_otp_code()
        email = signup_data['email']
        
        # Delete old unverified OTPs for this email/purpose
        EmailOTP.objects.filter(email=email, purpose='signup', verified=False).delete()
        
        # Create new OTP record
        EmailOTP.objects.create(email=email, code=otp_code, purpose='signup')
        
        # Send OTP email
        _send_otp_email(email, 'signup', otp_code)
        
        # Increment resend count in session
        request.session['otp_resend_count'] = otp_resend_count + 1
        request.session.modified = True
        
        return JsonResponse({
            'status': 'success',
            'message': 'A new OTP has been sent to your email.'
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to send OTP. Please try again later.'
        }, status=500)


def social_redirect(request, provider):
    provider = provider.lower()
    allowed_providers = ['google', 'microsoft']   # ← apple → microsoft

    if provider not in allowed_providers:
        messages.error(request, 'Unsupported social login provider.')
        return redirect('core:signup')

    return redirect(f'/accounts/{provider}/login/')


def otp_request(request):
    if request.method == 'POST':
        form = OTPRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            otp_code = _generate_otp_code()
            otp_created_at = timezone.now()
            request.session['otp_data'] = {
                'email': email,
                'code': otp_code,
                'created_at': otp_created_at.isoformat(),
                'attempts': 0,
            }
            subject = 'Your Nellie\'s Scent verification code'
            message = (
                f'Hello,\n\nYour OTP code is {otp_code}.\n'
                'Enter this code in the app to verify your email.\n\n'
                'This code expires in 5 minutes.\n\n'
                'If you did not request this code, please ignore this email.\n\n'
                'Thank you,\nNellie\'s Scent'
            )
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, 'OTP sent successfully. Check your email inbox.')
                return redirect('core:otp_verify')
            except Exception as exc:
                request.session.pop('otp_data', None)
                messages.error(request, 'Unable to send OTP email. Please verify your Gmail SMTP settings and try again.')
    else:
        form = OTPRequestForm()

    return render(request, 'account/otp_request.html', {
        'form': form,
        'cart_count': get_cart_count(request),
    })


def otp_verify(request):
    otp_data = request.session.get('otp_data')
    if not otp_data:
        messages.error(request, 'Please request a new OTP before verifying.')
        return redirect('core:otp_request')

    error_message = None
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code'].strip()
            otp_created_at = timezone.datetime.fromisoformat(otp_data['created_at'])
            if timezone.now() - otp_created_at > timedelta(minutes=5):
                request.session.pop('otp_data', None)
                error_message = 'Your OTP has expired. Please request a new code.'
            elif code != otp_data['code']:
                otp_data['attempts'] = otp_data.get('attempts', 0) + 1
                request.session['otp_data'] = otp_data
                error_message = 'The code is invalid. Please try again.'
            else:
                request.session.pop('otp_data', None)
                messages.success(request, 'Your OTP has been verified successfully.')
                return redirect('core:otp_success')
    else:
        form = OTPVerifyForm()

    return render(request, 'account/otp_verify.html', {
        'form': form,
        'error_message': error_message,
        'email': otp_data.get('email'),
        'cart_count': get_cart_count(request),
    })


@require_http_methods(["GET", "POST"])
def logout_user(request):
    """Logout user - supports both GET (link) and POST (form/AJAX)"""
    from django.contrib.auth import logout
    logout(request)
    
    if request.method == 'POST':
        return JsonResponse({'status': 'success', 'message': 'Logged out successfully'})
    
    return redirect('core:index')

def otp_success(request):
    return render(request, 'account/otp_success.html', {
        'cart_count': get_cart_count(request),
    })


def forgot_password_request(request):
    error_message = None
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email=email).first()
            if user:
                otp_code = _generate_otp_code()
                EmailOTP.objects.create(email=email, code=otp_code, purpose='password_reset')
                request.session['password_reset_email'] = email
                _send_otp_email(email, 'password_reset', otp_code)
                return redirect('core:forgot_password_verify')
            error_message = 'No account was found with that email address.'
    else:
        form = PasswordResetRequestForm()

    return render(request, 'account/forgot_password.html', {
        'form': form,
        'error_message': error_message,
        'cart_count': get_cart_count(request),
    })


def forgot_password_verify(request):
    email = request.session.get('password_reset_email')
    if not email:
        return redirect('core:forgot_password')

    error_message = None
    if request.method == 'POST':
        form = PasswordResetOTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            password1 = form.cleaned_data['password1']
            password2 = form.cleaned_data['password2']
            if password1 != password2:
                error_message = 'Passwords do not match.'
            elif _verify_otp(email, code, 'password_reset'):
                user = User.objects.filter(email=email).first()
                if user:
                    user.set_password(password1)
                    user.save()
                    request.session.pop('password_reset_email', None)
                    return redirect('account_login')
                error_message = 'Unable to find user account for this email.'
            else:
                error_message = 'The OTP code is invalid or expired. Please request a new one.'
    else:
        form = PasswordResetOTPForm()

    return render(request, 'account/forgot_password_verify.html', {
        'form': form,
        'error_message': error_message,
        'cart_count': get_cart_count(request),
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:index')
    
    form = CustomLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.user
        auth_login(request, user)
        
        # Merge session cart with user cart
        _merge_session_cart_with_user_cart(request, user)
        
        remember = form.cleaned_data.get('remember', False)
        if remember:
            request.session.set_expiry(0)  # persist until logout
        else:
            request.session.set_expiry(7200)  # 2 hours
        return redirect('core:index')
    elif request.method == 'POST':
        # If form is invalid (wrong credentials), add custom error message
        messages.error(request, "User credentials invalid")
    
    return render(request, 'account/login.html', {
        'form': form,
        'cart_count': get_cart_count(request),
    })


def contact(request):
    cart_count = get_cart_count(request)
    
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'core/contact.html', {
                'form': ContactForm(),
                'success': True,
                'cart_count': cart_count
            })
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {
        'form': form,
        'cart_count': cart_count
    })


def terms_of_service(request):
    cart_count = get_cart_count(request)
    return render(request, 'core/terms_of_service.html', {
        'cart_count': cart_count
    })


def privacy_policy(request):
    cart_count = get_cart_count(request)
    return render(request, 'core/privacy_policy.html', {
        'cart_count': cart_count
    })


def shop(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    cart_count = get_cart_count(request)
    
    products = Product.objects.all()
    
    # Filter by category if provided
    if category:
        products = products.filter(category=category)
    
    # Filter by search query if provided
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(product_type__icontains=query)
        )
    
    # Get all categories for filter display
    categories = Product.CATEGORY_CHOICES
    
    form = SearchForm(initial={'query': query})
    
    return render(request, 'core/shop.html', {
        'products': products,
        'form': form,
        'search_query': query,
        'categories': categories,
        'selected_category': category,
        'cart_count': cart_count
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    cart_count = get_cart_count(request)
    reviews = product.reviews.select_related('user').all()
    review_form = ReviewForm()
    review_success = False
    review_error = None

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('account_login')

        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            Review.objects.create(
                user=request.user,
                product=product,
                message=review_form.cleaned_data['message']
            )
            review_form = ReviewForm()
            review_success = True
        else:
            review_error = 'Please add your review message before submitting.'

    related_products = list(
        Product.objects.filter(mini_icon__isnull=False).exclude(id=product.id).order_by('?')[:3]
    )
    if len(related_products) < 3:
        related_fallback = Product.objects.filter(image__isnull=False).exclude(id__in=[product.id] + [p.id for p in related_products]).order_by('-created_at')[:3 - len(related_products)]
        related_products.extend(related_fallback)

    return render(request, 'core/product_detail.html', {
        'product': product,
        'cart_count': cart_count,
        'reviews': reviews,
        'review_form': review_form,
        'review_success': review_success,
        'review_error': review_error,
        'related_products': related_products,
    })


@require_http_methods(["POST"])
def add_to_cart(request):
    """Add product to cart via AJAX"""
    cart = _get_cart_from_session(request)

    try:
        # Handle both JSON and form data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            size = data.get('size')
        else:
            product_id = request.POST.get('product_id')
            quantity = int(request.POST.get('quantity', 1))
            size = request.POST.get('size')

        product = get_object_or_404(Product, id=product_id)
        cart_key = f"{product_id}_{size}"

        if request.user.is_authenticated:
            # Save to database for logged-in users
            existing_item = CartItem.objects.filter(
                user=request.user,
                product_id=product_id,
                size=size
            ).first()

            if existing_item:
                existing_item.quantity += quantity
                existing_item.save()
            else:
                CartItem.objects.create(
                    user=request.user,
                    product_id=product_id,
                    size=size,
                    quantity=quantity
                )
        else:
            # Save to session for anonymous users
            if cart_key in cart:
                cart[cart_key]['quantity'] += quantity
            else:
                cart[cart_key] = {
                    'product_id': int(product_id),
                    'name': product.name,
                    'price': str(product.price),
                    'size': size,
                    'quantity': quantity,
                    'image': product.image.url if product.image else ''
                }
            _save_cart_to_session(request, cart)

        # Build updated sidebar data so the frontend can refresh instantly
        updated_items = get_cart_items_with_products(request)
        subtotal = Decimal('0')
        sidebar_items = []
        for i in updated_items:
            item_total = i['product'].price * i['quantity']
            subtotal += item_total
            sidebar_items.append({
                'name': i['product'].name,
                'image': i['product'].image.url if i['product'].image else '',
                'size': i['size'],
                'quantity': i['quantity'],
                'total': str(item_total),
            })

        return JsonResponse({
            'status': 'success',
            'message': f'{product.name} added to cart',
            'cart_count': get_cart_count(request),
            'show_login_message': not request.user.is_authenticated,
            'sidebar_items': sidebar_items,
            'sidebar_subtotal': str(subtotal),
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@require_http_methods(["POST"])
def update_cart(request):
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            cart_key = data.get('cart_key')
            quantity = int(data.get('quantity', 1))
        else:
            cart_key = request.POST.get('cart_key')
            quantity = int(request.POST.get('quantity', 1))

        if request.user.is_authenticated:
            product_id, size = cart_key.rsplit('_', 1)
            item = CartItem.objects.filter(
                user=request.user, product_id=product_id, size=size
            ).first()
            if item:
                if quantity <= 0:
                    item.delete()
                else:
                    item.quantity = quantity
                    item.save()
        else:
            cart = _get_cart_from_session(request)
            if quantity <= 0:
                cart.pop(cart_key, None)
            elif cart_key in cart:
                cart[cart_key]['quantity'] = quantity
            _save_cart_to_session(request, cart)

        return JsonResponse({'status': 'success', 'cart_count': get_cart_count(request)})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@require_http_methods(["POST"])
def remove_from_cart(request):
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            cart_key = data.get('cart_key')
        else:
            cart_key = request.POST.get('cart_key')

        if request.user.is_authenticated:
            product_id, size = cart_key.rsplit('_', 1)
            CartItem.objects.filter(
                user=request.user, product_id=product_id, size=size
            ).delete()
        else:
            cart = _get_cart_from_session(request)
            cart.pop(cart_key, None)
            _save_cart_to_session(request, cart)

        return JsonResponse({'status': 'success', 'cart_count': get_cart_count(request)})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_http_methods(["GET"])
def get_cart_data(request):
    """Get cart data for AJAX requests (sidebar update)"""
    try:
        cart_items = get_cart_items_with_products(request)
        subtotal = Decimal('0')
        items_response = []

        for item in cart_items:
            item_total = item['product'].price * item['quantity']
            subtotal += item_total
            items_response.append({
                'cart_key': item['cart_key'],
                'name': item['product'].name,
                'image': item['product'].image.url if item['product'].image else '',
                'size': item['size'],
                'quantity': item['quantity'],
                'price': str(item['product'].price),
                'total': str(item_total),
            })

        return JsonResponse({
            'status': 'success',
            'cart_items': items_response,
            'cart_count': get_cart_count(request),
            'cart_subtotal': str(subtotal),
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def view_cart(request):
    """View cart items"""
    print(f"=== VIEW_CART DEBUG START ===")
    print(f"SESSION KEY: {request.session.session_key}")
    print(f"RAW SESSION CART: {request.session.get('cart')}")
    
    cart_items = get_cart_items_with_products(request)
    print(f"CART ITEMS RETRIEVED: {len(cart_items)} items")
    
    total = Decimal('0')
    for item in cart_items:
        # Calculate total from cart items (works for both DB and session)
        item_price = Decimal(item['product'].price)
        total += item_price * Decimal(item['quantity'])
    
    subtotal_ngn = f"₦{total:,.2f}"
    total_ngn = f"₦{total:,.2f}"
    cart_count = get_cart_count(request)
    
    print(f"=== VIEW_CART DEBUG END ===")
    
    return render(request, 'core/cart.html', {
        'cart_items': cart_items,
        'subtotal': total,
        'subtotal_ngn': subtotal_ngn,
        'total': total,
        'total_ngn': total_ngn,
        'cart_count': cart_count
    })


# views.py — checkout()

def checkout(request):
    cart_items = get_cart_items_with_products(request)  # ← use this, not session

    if not cart_items:
        return redirect('core:shop')

    # Build total from cart_items (works for both DB and session users)
    total = sum(
        item['product'].price * item['quantity']
        for item in cart_items
    )
    cart_count = get_cart_count(request)
    subtotal_ngn = f"₦{total:,.2f}"
    total_ngn = f"₦{total:,.2f}"

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.status = 'pending'
            order.save()

            for item in cart_items:  # ← loop over cart_items, not session
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    quantity=item['quantity'],
                    price=item['product'].price,
                    size=item['size']
                )

            # Clear cart — both session AND database
            request.session['cart'] = {}
            request.session.modified = True
            if request.user.is_authenticated:
                CartItem.objects.filter(user=request.user).delete()

            return redirect('core:initiate_payment', order_id=order.id)
    else:
        form = CheckoutForm()

    return render(request, 'core/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'subtotal_ngn': subtotal_ngn,
        'total_ngn': total_ngn,
        'order_total': total,
        'cart_count': cart_count
    })

def checkout_success(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id)
    items = order.orderitem_set.all()
    cart_count = 0  # Cart is empty after checkout
    
    return render(request, 'core/checkout_success.html', {
        'order': order,
        'items': items,
        'cart_count': cart_count
    })


def initiate_payment(request, order_id):
    """Initialize Paystack payment"""
    order = get_object_or_404(Order, id=order_id, status='pending')
    
    # Amount in kobo (multiply by 100)
    amount_kobo = int(order.get_total() * 100)
    
    # Paystack transaction initialization
    import requests
    from django.conf import settings
    
    url = f"{settings.PAYSTACK_BASE_URL}/transaction/initialize"
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'email': order.email,
        'amount': amount_kobo,
        'reference': f"order_{order.id}_{order.created_at.strftime('%Y%m%d%H%M%S')}",
        'callback_url': request.build_absolute_uri(f'/payment/verify/{order.id}/'),
        'metadata': {
            'order_id': order.id,
            'custom_fields': [
                {
                    'display_name': 'Order ID',
                    'variable_name': 'order_id',
                    'value': order.id
                }
            ]
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    result = response.json()
    
    if result['status']:
        # Save transaction reference
        order.transaction_ref = result['data']['reference']
        order.save()
        
        # Redirect to Paystack payment page
        return redirect(result['data']['authorization_url'])
    else:
        # Payment initialization failed
        return render(request, 'core/payment_error.html', {
            'error': 'Payment initialization failed. Please try again.',
            'order': order
        })


def verify_payment(request, order_id):
    """Verify Paystack payment"""
    order = get_object_or_404(Order, id=order_id)
    
    reference = request.GET.get('reference')
    if not reference:
        return render(request, 'core/payment_error.html', {
            'error': 'No payment reference provided.',
            'order': order
        })
    
    # Verify payment with Paystack
    import requests
    from django.conf import settings
    
    url = f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}"
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'
    }
    
    response = requests.get(url, headers=headers)
    result = response.json()
    
    if result['status'] and result['data']['status'] == 'success':
        # Payment successful
        order.status = 'confirmed'
        order.payment_status = 'success'
        order.amount_paid = Decimal(result['data']['amount']) / 100  # Convert from kobo
        order.save()
        
        return redirect('core:checkout_success', order_id=order.id)
    else:
        # Payment failed
        order.payment_status = 'failed'
        order.save()
        
        return render(request, 'core/payment_error.html', {
            'error': 'Payment verification failed. Please try again.',
            'order': order
        })


def _parse_dashboard_range(request):
    range_key = request.GET.get('range', '7')
    custom_start = request.GET.get('start')
    custom_end = request.GET.get('end')
    today = timezone.localtime(timezone.now()).date()

    if range_key == 'today':
        start_date = today
        end_date = today
    elif range_key == '7':
        start_date = today - timedelta(days=6)
        end_date = today
    elif range_key == '30':
        start_date = today - timedelta(days=29)
        end_date = today
    elif range_key == 'custom' and custom_start and custom_end:
        try:
            start_date = datetime.strptime(custom_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(custom_end, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=6)
            end_date = today
    else:
        start_date = today - timedelta(days=6)
        end_date = today

    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def dashboard_summary(request):
    start_date, end_date = _parse_dashboard_range(request)
    confirmed_orders = Order.objects.filter(status='confirmed', created_at__date__gte=start_date, created_at__date__lte=end_date)

    orders_today = Order.objects.filter(status='confirmed', created_at__date=timezone.localtime(timezone.now()).date()).count()

    total_revenue_today = OrderItem.objects.filter(order__status='confirmed', order__created_at__date=timezone.localtime(timezone.now()).date())\
        .aggregate(total=Sum(F('price') * F('quantity'), output_field=DecimalField()))['total'] or Decimal('0')

    total_revenue_overall = OrderItem.objects.filter(order__status='confirmed')\
        .aggregate(total=Sum(F('price') * F('quantity'), output_field=DecimalField()))['total'] or Decimal('0')

    return JsonResponse({
        'orders_today': orders_today,
        'revenue_today': float(total_revenue_today),
        'revenue_overall': float(total_revenue_overall),
    })


def dashboard_orders_per_day(request):
    start_date, end_date = _parse_dashboard_range(request)
    data = Order.objects.filter(status='confirmed', created_at__date__gte=start_date, created_at__date__lte=end_date)\
        .annotate(day=TruncDate('created_at'))\
        .values('day')\
        .annotate(count=Count('id'))\
        .order_by('day')

    labels = [entry['day'].strftime('%Y-%m-%d') for entry in data]
    counts = [entry['count'] for entry in data]

    return JsonResponse({'labels': labels, 'data': counts})


def dashboard_revenue_per_day(request):
    start_date, end_date = _parse_dashboard_range(request)
    data = OrderItem.objects.filter(order__status='confirmed', order__created_at__date__gte=start_date, order__created_at__date__lte=end_date)\
        .annotate(day=TruncDate('order__created_at'))\
        .values('day')\
        .annotate(revenue=Sum(F('price') * F('quantity'), output_field=DecimalField()))\
        .order_by('day')

    labels = [entry['day'].strftime('%Y-%m-%d') for entry in data]
    revenue = [float(entry['revenue'] or 0) for entry in data]

    return JsonResponse({'labels': labels, 'data': revenue})


def dashboard_category_revenue(request):
    start_date, end_date = _parse_dashboard_range(request)

    category_map = {
        'designer_perfumes': 'Designer Perfumes',
        'arabian_perfumes': 'Arabian Perfumes',
        'body_mists': 'Body Mists',
        'gift_products': 'Gift Products',
        'car_fresheners': 'Car Fresheners',
        'oil_perfumes': 'Oil Perfumes',
    }

    data = OrderItem.objects.filter(order__status='confirmed', order__created_at__date__gte=start_date, order__created_at__date__lte=end_date)\
        .values('product__category')\
        .annotate(revenue=Sum(F('price') * F('quantity'), output_field=DecimalField()))

    labels = []
    values = []

    for entry in data:
        category_key = entry['product__category']
        labels.append(category_map.get(category_key, category_key or 'Unknown'))
        values.append(float(entry['revenue'] or 0))

    return JsonResponse({'labels': labels, 'data': values})


def dashboard_top_products(request):
    start_date, end_date = _parse_dashboard_range(request)

    data = OrderItem.objects.filter(order__status='confirmed', order__created_at__date__gte=start_date, order__created_at__date__lte=end_date)\
        .values('product__name')\
        .annotate(quantity=Sum('quantity'))\
        .order_by('-quantity')[:10]

    labels = [entry['product__name'] for entry in data]
    quantities = [entry['quantity'] for entry in data]

    return JsonResponse({'labels': labels, 'data': quantities})


# ============ CUSTOM ADMIN DASHBOARD VIEWS ============

from django.contrib.auth.decorators import login_required
from functools import wraps


def admin_required(view_func):
    """Decorator to ensure only admin users can access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('admin:login')
        return view_func(request, *args, **kwargs)
    return wrapper


@require_http_methods(["POST"])
def undo_admin_change(request):
    """Undo the last admin change within 10 seconds"""
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        model_name = data.get('model_name')
        object_id = data.get('object_id')

        if not model_name or not object_id:
            return JsonResponse({'status': 'error', 'message': 'model_name and object_id are required'}, status=400)

        # Find the most recent valid undo record
        undo_data = UndoData.objects.filter(
            model_name=model_name,
            object_id=object_id
        ).order_by('-created_at').first()

        if not undo_data:
            return JsonResponse({'status': 'error', 'message': 'No undo record found for this object'}, status=404)

        if not undo_data.is_valid():
            undo_data.delete()  # Clean up expired record
            return JsonResponse({'status': 'error', 'message': 'Undo window has expired (10 seconds)'}, status=400)

        # Restore the Product fields from previous_data
        if model_name == 'Product':
            product = get_object_or_404(Product, id=object_id)
            previous = undo_data.previous_data

            field_map = {
                'name': str,
                'slug': str,
                'description': str,
                'size': str,
                'product_type': str,
                'category': str,
            }

            for field, cast in field_map.items():
                if field in previous:
                    setattr(product, field, cast(previous[field]) if previous[field] is not None else '')

            if 'price' in previous:
                setattr(product, 'price', Decimal(str(previous['price'])) if previous['price'] is not None else Decimal('0'))

            if 'stock' in previous:
                setattr(product, 'stock', int(previous['stock']) if previous['stock'] is not None else 0)

            product.save()

        else:
            return JsonResponse({'status': 'error', 'message': f'Undo not supported for model: {model_name}'}, status=400)

        # Delete the used undo record
        undo_data.delete()

        return JsonResponse({'status': 'success', 'message': f'{model_name} #{object_id} restored successfully'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


