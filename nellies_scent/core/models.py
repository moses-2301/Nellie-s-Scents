import os
from datetime import timedelta
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth.models import User
from PIL import Image


class Product(models.Model):
    SIZE_CHOICES = [
        ('30ml', '30ml'),
        ('50ml', '50ml'),
        ('100ml', '100ml'),
    ]
    
    TYPE_CHOICES = [
        ('', 'None'),
        ('eau_de_parfum', 'Eau de Parfum'),
        ('eau_de_toilette', 'Eau de Toilette'),
        ('body_spray', 'Body Spray'),
    ]
    
    CATEGORY_CHOICES = [
        ('designer_perfumes', 'Designer Perfumes'),
        ('arabian_perfumes', 'Arabian Perfumes'),
        ('body_mists', 'Body Mists'),
        ('gift_products', 'Gift Products'),
        ('car_fresheners', 'Car Fresheners'),
        ('oil_perfumes', 'Oil Perfumes'),
    ]
    
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(blank=True)
    size = models.CharField(max_length=20, default='50ml')
    product_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='eau_de_parfum', blank=True)
    category = models.CharField(max_length=35, choices=CATEGORY_CHOICES, default='designer_perfumes')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    mini_icon = models.ImageField(upload_to='product-icons/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name

    def _generate_unique_slug(self):
        base_slug = slugify(self.name)
        slug = base_slug
        count = 1
        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{count}"
            count += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()

        if self.mini_icon and hasattr(self.mini_icon, 'file'):
            self.mini_icon.open()
            image = Image.open(self.mini_icon)
            image = image.convert('RGB')

            target_width, target_height = 342, 202
            image.thumbnail((target_width, target_height), Image.LANCZOS)

            background = Image.new('RGB', (target_width, target_height), (255, 255, 255))
            offset = ((target_width - image.width) // 2, (target_height - image.height) // 2)
            background.paste(image, offset)

            buffer = BytesIO()
            background.save(buffer, format='JPEG', quality=90)
            buffer.seek(0)

            icon_name = os.path.splitext(self.mini_icon.name)[0] + '.jpg'
            self.mini_icon.save(icon_name, ContentFile(buffer.read()), save=False)
            image.close()
            background.close()
            buffer.close()

        super().save(*args, **kwargs)

    def get_price_ngn(self):
        """Format price in Nigerian Naira"""
        return f"₦{self.price:,.2f}"
    
    def get_category_display_name(self):
        """Get category display name"""
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category)

    def get_absolute_url(self):
        return f"/product/{self.slug}/"

    def get_mini_icon_url(self):
        if self.mini_icon:
            return self.mini_icon.url
        if self.image:
            return self.image.url
        return ''


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'

    def __str__(self):
        return f"Review by {self.user.username} on {self.product.name}"


class EmailOTP(models.Model):
    PURPOSE_CHOICES = [
        ('signup', 'Signup'),
        ('password_reset', 'Password Reset'),
    ]

    email = models.EmailField()
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email OTP'
        verbose_name_plural = 'Email OTPs'

    def __str__(self):
        return f"{self.purpose.title()} OTP for {self.email}"

    def is_valid(self):
        expiry = timezone.now() - timedelta(minutes=10)
        return not self.verified and self.created_at >= expiry


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return f"Message from {self.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=120)
    email = models.EmailField(default='')
    phone = models.CharField(max_length=20)
    address = models.TextField()
    state = models.CharField(max_length=50)
    payment_method = models.CharField(max_length=20, choices=[('card', 'Card'), ('bank', 'Bank Transfer')])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_ref = models.CharField(max_length=100, blank=True, null=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"

    def get_total(self):
        """Calculate total price"""
        return sum(item.get_total() for item in self.orderitem_set.all())

    def get_total_ngn(self):
        """Get formatted total in NGN"""
        total = self.get_total()
        return f"₦{total:,.2f}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    size = models.CharField(max_length=10)

    class Meta:
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def get_total(self):
        return self.price * self.quantity

    def get_total_ngn(self):
        total = self.get_total()
        return f"₦{total:,.2f}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} Profile"


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=10)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'size')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.size})"

    def get_total(self):
        return self.product.price * self.quantity

    def get_total_ngn(self):
        return f"₦{self.get_total():,.2f}"


class UndoData(models.Model):
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField()
    previous_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Undo Data'
        verbose_name_plural = 'Undo Data'

    def __str__(self):
        return f"Undo for {self.model_name} #{self.object_id}"

    def is_valid(self):
        """Check if undo is still valid (within 10 seconds)"""
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() - self.created_at < timedelta(seconds=10)

