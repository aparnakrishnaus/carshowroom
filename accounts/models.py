from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.utils import timezone

# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, role='customer', **extra_fields):
        if not username:
            raise ValueError("The Username must be set")
        role = extra_fields.pop('role', role)
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields['role'] = 'admin'
        return self.create_user(username, email, password, **extra_fields)


# ----------------------------
# Custom User model
# ----------------------------
class User(AbstractUser):
 
    ROLE_CUSTOMER = 'customer'
    ROLE_STAFF = 'staff'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_STAFF, 'Staff'),
        (ROLE_ADMIN, 'Admin'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    objects = UserManager()
    is_removed = models.BooleanField(default=False)



   #cars     
CAR_CATEGORIES = [
    ('basic', 'Basic'),
    ('premium', 'Premium'),
    ('luxury', 'Luxury'),
]

class Car(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CAR_CATEGORIES, default='basic')
    image = models.ImageField(upload_to='cars/main_images/')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    featured = models.BooleanField(default=False)
    brand = models.CharField(max_length=100, blank=True, null=True)
    model_year = models.PositiveIntegerField(blank=True, null=True)
    engine_type = models.CharField(max_length=100, blank=True, null=True)
    transmission = models.CharField(max_length=50, blank=True, null=True)
    fuel_type = models.CharField(max_length=50, blank=True, null=True)
    mileage = models.CharField(max_length=50, blank=True, null=True)
    seats = models.PositiveIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    search_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='extra_images')
    image = models.ImageField(upload_to='cars/extra_images/')

    def __str__(self):
        return f"Extra image for {self.car.name}"
    
    
# profile
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_pics/',  blank=True, null=True)

    def __str__(self):
        return self.user.username
    


# booking
class Booking(models.Model):
    BOOKING_TYPE_CHOICES = [
        ('book', 'Book Car'),
        ('rent', 'Rent Car'),
        ('test_drive', 'Test Drive'),
        ('service', 'Service Booking'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('Cancelled by Admin', 'Cancelled by Admin'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    car = models.ForeignKey(Car, on_delete=models.CASCADE,null=True, blank=True)
    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES, default='book')
    service = models.ForeignKey('Service', on_delete=models.CASCADE, null=True, blank=True)
    
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(blank=True, null=True)
    duration_days = models.PositiveIntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_active = models.BooleanField(default=True)
    is_removed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    duration = models.CharField(max_length=50, blank=True, null=True) 

    name = models.CharField(max_length=100, blank=True, null=True, default='Your Name')
    email = models.EmailField(blank=True, null=True, default='example@example.com')
    phone = models.CharField(max_length=20, blank=True, null=True, default='0000000000')
    pickup_location = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    advance_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_fully_paid = models.BooleanField(default=False)
    is_advance_paid = models.BooleanField(default=False)

    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)

    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    refund_requested = models.BooleanField(default=False) 
    is_refunded = models.BooleanField(default=False)
    cancel_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.booking_type})"


# wishlist
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    car =models.ForeignKey(Car, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user','car')

    def __str__(self):
        return f"{self.user.username} - {self.car.name}"
    

# services
class Service(models.Model):
    CATEGORY_CHOICES = [
        ('maintenance', 'Maintenance'),
        ('detailing', 'Detailing'),
        ('repair', 'Repair'),
        ('customization', 'Customization'),
        ('premium', 'Premium'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2 ,default=0)
    duration = models.CharField(max_length=50, help_text="Example: 2 hrs, 30 mins")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(blank=True, null=True)
    price_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    process_steps = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    search_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name
    

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.name}"
    
class Review(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE, null=True, blank=True)
    spare_booking = models.ForeignKey('BookedSparePart', on_delete=models.CASCADE, null=True, blank=True)
    rating = models.IntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')


    def __str__(self):
        return f"{self.user.username} - {self.rating}★"
    

class SparePart(models.Model):
    CATEGORY_CHOICES = [
        ('engine', 'Engine & Related'),
        ('transmission', 'Transmission & Drivetrain'),
        ('brakes', 'Brakes'),
        ('suspension', 'Suspension & Steering'),
        ('wheels', 'Wheels & Tires'),
        ('electrical', 'Electrical & Lighting'),
        ('cooling', 'Cooling & AC'),
        ('belts_hoses', 'Belts & Hoses'),
        ('misc', 'Miscellaneous'),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, null=True)
    available = models.BooleanField(default=True)
    search_count = models.PositiveIntegerField(default=0)


    def __str__(self):
        return f"{self.name} ({self.category})"
    

class BookedSparePart(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('delivered', 'Delivered'),
        ('Cancelled by User', 'Cancelled by User'), 
        ('Refunded', 'Refunded'),
    ]

    part = models.ForeignKey('SparePart', on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    customer_name = models.CharField(max_length=150, default="N/A")
    email = models.EmailField(default="not_provided@example.com")
    car_name = models.CharField(max_length=100, default="Unknown Car")
    address = models.TextField(default="Address not provided")
    phone = models.CharField(max_length=20, blank=True, null=True, default='0000000000')

    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')
    payment_method = models.CharField(max_length=20, choices=[('cod','Cash on Delivery'),('online','Online Payment')], default='cod')

    # Timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)     

    is_removed = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)

    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    deleted_by_user = models.BooleanField(default=False)
    refund_requested = models.BooleanField(default=False) 
    is_refunded = models.BooleanField(default=False)
    cancel_reason = models.TextField(blank=True, null=True)



    def __str__(self):
        return f"{self.part.name} booked by {self.customer_name}"
    


class NewsletterSubscriber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(unique=True)
    is_subscribed = models.BooleanField(default=True)
    subscribed_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
    
class NewsletterMessage(models.Model):
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subject

    





