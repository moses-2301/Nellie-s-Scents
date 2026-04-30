from django.shortcuts import redirect
from django.utils.html import format_html
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Product, ContactMessage, Order, OrderItem, Review, EmailOTP, Profile, UndoData
import json


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_display', 'price_display', 'size', 'product_type', 'stock', 'created_at', 'image_preview', 'mini_icon_preview')
    search_fields = ('name', 'description')
    list_filter = ('category', 'created_at', 'size', 'product_type')
    ordering = ('-created_at',)
    list_per_page = 20
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'image_preview', 'mini_icon_preview')
    prepopulated_fields = {'slug': ('name',)}

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'size' in form.base_fields:
            form.base_fields['size'].widget = forms.TextInput(attrs={'class': 'vTextField'})
        return form

    fieldsets = (
        ('Product Details', {
            'fields': ('name', 'slug', 'description', 'image', 'mini_icon', 'image_preview', 'mini_icon_preview')
        }),
        ('Classification', {
            'fields': ('category', 'size', 'product_type')
        }),
        ('Stock & Pricing', {
            'fields': ('price', 'stock')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def category_display(self, obj):
        return obj.get_category_display_name()
    category_display.short_description = 'Category'

    def price_display(self, obj):
        return format_html('<strong>{}</strong>', obj.get_price_ngn())
    price_display.short_description = 'Price (NGN)'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 150px; object-fit: contain;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Image Preview'

    def mini_icon_preview(self, obj):
        if obj.mini_icon:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 150px; object-fit: contain;" />', obj.mini_icon.url)
        return '-'
    mini_icon_preview.short_description = 'Mini Icon Preview'

    def save_model(self, request, obj, form, change):
        if change:  # Only store undo data for updates, not new objects
            # Store previous data for undo
            previous_data = {}
            for field in obj._meta.fields:
                if field.name not in ['updated_at']:
                    value = getattr(obj, field.name)
                    if hasattr(value, 'url'):  # FileField
                        previous_data[field.name] = value.url if value else None
                    else:
                        previous_data[field.name] = str(value) if value is not None else None
            
            UndoData.objects.create(
                model_name='Product',
                object_id=obj.id,
                previous_data=previous_data
            )
        
        super().save_model(request, obj, form, change)
        
        # Redirect with saved parameter to trigger undo notification
        if change:
            return redirect(f'{request.path}?saved=1')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'is_read_status')
    search_fields = ('name', 'email', 'message')
    list_filter = ('created_at', 'is_read')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'name', 'email', 'message')
    fieldsets = (
        ('Message Details', {
            'fields': ('name', 'email', 'message')
        }),
        ('Status', {
            'fields': ('is_read', 'created_at')
        }),
    )
    
    def is_read_status(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: red;">✗ Unread</span>')
    is_read_status.short_description = 'Status'

    actions = ['mark_as_read', 'mark_as_unread', 'delete_messages']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = 'Mark as read'

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = 'Mark as unread'

    def delete_messages(self, request, queryset):
        count = queryset.count()
        if count == 1:
            message = f"Are you sure you want to delete this message?"
        else:
            message = f"Are you sure you want to delete these {count} messages?"
        
        # Use Django's delete_selected action which already has confirmation
        from django.contrib.admin.actions import delete_selected
        return delete_selected(self, request, queryset)
    delete_messages.short_description = 'Delete selected messages'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'size')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'customer_name', 'phone', 'state', 'payment_method', 'status_display', 'total_display', 'created_at')
    search_fields = ('full_name', 'phone', 'address')
    list_filter = ('status', 'created_at', 'payment_method')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'user', 'total_display')
    fieldsets = (
        ('Order Information', {
            'fields': ('user', 'status')
        }),
        ('Customer Details', {
            'fields': ('full_name', 'phone', 'address', 'state')
        }),
        ('Payment', {
            'fields': ('payment_method', 'total_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [OrderItemInline]

    def order_id(self, obj):
        return format_html('<strong>#{}</strong>', obj.id)
    order_id.short_description = 'Order ID'

    def customer_name(self, obj):
        return obj.full_name
    customer_name.short_description = 'Customer'

    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'completed': 'green',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'grey')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def total_display(self, obj):
        return format_html('<strong>{}</strong>', obj.get_total_ngn())
    total_display.short_description = 'Total Amount'
    
    def changelist_view(self, request, extra_context=None):
        """Add analytics to the order list view"""
        extra_context = extra_context or {}
        
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        
        # Calculate today's statistics
        orders_today = Order.objects.filter(
            status='confirmed',
            created_at__gte=today_start,
            created_at__lte=today_end
        )
        
        total_revenue_today = Decimal('0')
        for order in orders_today:
            total_revenue_today += order.get_total()
        
        # Calculate overall statistics (only completed orders)
        all_completed_orders = Order.objects.filter(status='confirmed')
        total_revenue_overall = Decimal('0')
        for order in all_completed_orders:
            total_revenue_overall += order.get_total()
        
        extra_context.update({
            'orders_today': orders_today.count(),
            'revenue_today': f"₦{total_revenue_today:,.2f}",
            'revenue_overall': f"₦{total_revenue_overall:,.2f}",
        })
        
        return super().changelist_view(request, extra_context)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'message', 'created_at')
    search_fields = ('user__username', 'product__name', 'message')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'user', 'product', 'message')


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'purpose', 'code', 'verified', 'created_at')
    list_filter = ('purpose', 'verified', 'created_at')
    search_fields = ('email', 'code')
    readonly_fields = ('created_at',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_verified')
    list_filter = ('is_verified',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user',)


admin.site.site_header = "Nellie's Scent Management"
admin.site.site_title = "Nellie's Scent Admin"
admin.site.index_title = "Nellie's Scent Dashboard"


# Admin customization to show analytics
class NellieScentsAdminSite(admin.AdminSite):
    site_header = "Nellie's Scent Management"
    site_title = "Nellie's Scent Admin"
    
    def index(self, request, extra_context=None):
        """Custom admin index with analytics"""
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        
        # Calculate analytics
        total_orders_today = Order.objects.filter(
            status='confirmed',
            created_at__gte=today_start,
            created_at__lte=today_end
        ).count()
        
        total_revenue_today = Order.objects.filter(
            status='confirmed',
            created_at__gte=today_start,
            created_at__lte=today_end
        ).aggregate(total=Sum('orderitem__price'))['total'] or Decimal('0')
        
        # Calculate total quantity for total revenue
        total_revenue_today_calc = Decimal('0')
        for order in Order.objects.filter(status='confirmed', created_at__gte=today_start, created_at__lte=today_end):
            total_revenue_today_calc += order.get_total()
        
        total_revenue_overall = Decimal('0')
        for order in Order.objects.filter(status='confirmed'):
            total_revenue_overall += order.get_total()
        
        extra_context = extra_context or {}
        extra_context.update({
            'total_orders_today': total_orders_today,
            'total_revenue_today': f"₦{total_revenue_today_calc:,.2f}",
            'total_revenue_overall': f"₦{total_revenue_overall:,.2f}",
            'total_products': Product.objects.count(),
            'total_messages': ContactMessage.objects.filter(is_read=False).count(),
        })
        
        return super().index(request, extra_context)

