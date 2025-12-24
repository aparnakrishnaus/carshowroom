
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.contrib.auth import logout
import json
from django.db.models import F
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.mail import send_mail
from django.forms import modelformset_factory
from django.db import IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.dateparse import parse_date
from django.db.models import Sum, Count ,F
from datetime import date
from .models import SparePart
from django.utils import timezone
from django.utils.text import slugify
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from .models import Booking
from .models import Car, CarImage, User, Wishlist
from .models import ContactMessage
from .models import Review
from .models import Car
from django.db.models import Q
from .models import NewsletterSubscriber, NewsletterMessage
from django.core.mail import send_mass_mail
from .models import Service
from .models import BookedSparePart
from collections import defaultdict
from django.http import JsonResponse
import razorpay
from django.conf import settings as django_settings
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from razorpay.errors import SignatureVerificationError
from collections import defaultdict

from .forms import (
    CustomerSignUpForm, 
    CarForm, 
    CarImageForm,
    AdminProfileForm,
    AdminProfileImageForm,
    Profile,
    BookingForm
)

# _________________ User Authentication ________________________________________________________

def register_view(request):
    if request.method == 'POST':
        form = CustomerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'customer'
            user.save()
            messages.success(request, 'Account created. Please login.')
            return redirect('login')
    else:
        form = CustomerSignUpForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    storage = messages.get_messages(request)
    list(storage) 
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f"Hi {user.username}, welcome to PrestigeLane! You are now logged in.")
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'accounts/login.html')


def logout_view(request):
    username = request.user.username if request.user.is_authenticated else ''
    logout(request)
    
    if username:
        messages.info(request, f"{username}, you have been successfully logged out.")
    else:
        messages.info(request, "You have been successfully logged out.")
    
    return redirect('home')

# _________________________________________________________________________

def admin_only(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You are not allowed to access this page.")
            return redirect("staff_dashboard")  
    return wrapper

def staff_only(view_func):
    return user_passes_test(lambda u: u.is_staff and not u.is_superuser)(view_func)

def admin_or_staff_required(view_func):
    return user_passes_test(lambda u: u.is_staff or u.is_superuser)(view_func)


@login_required
def dashboard_redirect(request):
    user = request.user
    if user.is_superuser:
        return redirect('admin_dashboard')
    elif user.is_staff:
        return redirect('staff_dashboard')
    else:
        return redirect('home')


@login_required
def user_dashboard(request):
    cars = Car.objects.all()
    profile = request.user.profile
    return render(request, "accounts/home.html", {"cars": cars, "profile": profile})


@login_required
@user_passes_test(lambda u: u.is_staff)
def staff_dashboard(request):
    messages_count = ContactMessage.objects.count()
    today = date.today()

    todays_bookings = Booking.objects.filter(
        date=today,
        is_removed=False
        ).exclude(status='Cancelled by Admin').order_by('-created_at')
    
    total_cars = Car.objects.count()
    cars_sold = Booking.objects.filter(booking_type='book', status='Completed').count()
    pending_bookings = Booking.objects.filter(
        status__iexact='pending', 
        is_removed=False
    )
    pending_count = pending_bookings.count()
    total_staff = User.objects.filter(is_staff=True).count()
    
    context = {
        "messages_count": messages_count,
        'cars_sold': cars_sold,
        'total_cars': total_cars,
        'pending_bookings': pending_count,
        'total_staff': total_staff,
        'todays_bookings': todays_bookings,
    }
    return render(request, "admin/admin_dashboard.html",context)


@admin_or_staff_required
def admin_dashboard(request):
    messages_count = ContactMessage.objects.count()
    today = date.today()
    
    todays_bookings = Booking.objects.filter(
        date=today,
        is_removed=False
        ).exclude(status='Cancelled by Admin').order_by('-created_at')
    
    total_cars = Car.objects.count()
    cars_sold = Booking.objects.filter(booking_type='book', status='Completed').count()
    pending_bookings = Booking.objects.filter(
        status__iexact='pending', 
        is_removed=False
    )
    pending_count = pending_bookings.count()
    total_staff = User.objects.filter(is_staff=True).count()
    
    context = {
        'total_cars': total_cars,
        'cars_sold': cars_sold,
        'pending_bookings': pending_count,
        'total_staff': total_staff,
        'todays_bookings': todays_bookings,
        'show_profile': False,  
        'messages_count': messages_count,
    }
    return render(request, "admin/admin_dashboard.html", context)

class AdminPasswordChangeView(PasswordChangeView):
    template_name = "accounts/admin_change_password.html" 
    success_url = reverse_lazy("login") 

    def form_valid(self, form):
        form.save()         
        logout(self.request) 
        messages.success(self.request, "Password changed successfully. Please log in again.")
        return redirect(self.success_url)


# _______________________ Admin __________________________________________________

@admin_only
def manage_users(request, role):
    messages_count = ContactMessage.objects.count()
    if role not in ['staff', 'admin', 'superuser']:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not email or not password:
            messages.error(request, "All fields are required!")
            return redirect('manage_users', role=role)

        try:
            if role == 'staff':
                if User.objects.filter(username=username, is_staff=True, is_superuser=False, is_removed=False        ).exists():
                    messages.error(request, f"A staff member named '{username}' already exists!")
                    return redirect('manage_users', role=role)
                User.objects.create_user(username=username, email=email, password=password, is_staff=True, role='staff')

            elif role in ['admin', 'superuser']:
                if User.objects.filter(username=username, is_superuser=True, is_removed=False        ).exists():
                    messages.error(request, f"An admin named '{username}' already exists!")
                    return redirect('manage_users', role=role)
                User.objects.create_superuser(username=username, email=email, password=password,  role='admin')

            messages.success(request, f"{role.title()} added successfully!")
            return redirect('manage_users', role=role)

        except IntegrityError:
            messages.error(request, f"The username '{username}' already exists! Please choose a different one.")
            return redirect('manage_users', role=role)

    users = (
        User.objects.filter(is_staff=True, is_superuser=False, is_removed=False)
        if role == 'staff'
        else User.objects.filter(is_superuser=True, is_removed=False)
    )

    return render(request, 'admin/manage_users.html', {'users': users, 'role': role, "messages_count":messages_count,})


@admin_only
def edit_user(request, user_id, role):
    if role == "staff":
        user = get_object_or_404(User, id=user_id, is_staff=True, is_superuser=False)
    else:
        user = get_object_or_404(User, id=user_id, is_superuser=True)

    if request.method == "POST":
        user.username = request.POST.get("username").strip()
        user.email = request.POST.get("email").strip()
        new_password = request.POST.get("password").strip()
        if new_password:
            user.set_password(new_password)
        user.save()
        messages.success(request, f"{role.title()} updated successfully!")
        return redirect('manage_users', role=role)

    return render(request, "admin/edit_user.html", {"user_obj": user, "role": role})


@admin_only
def delete_user(request, user_id, role):
    if role == "staff":
        user = get_object_or_404(User, id=user_id, is_staff=True, is_superuser=False)
    else:
        user = get_object_or_404(User, id=user_id, is_superuser=True)

    if request.user == user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('manage_users', role=role)
    
    user.is_removed = True
    user.is_active = False
    user.save()

    messages.success(request, f"{role.title()} moved to trash.")
    return redirect('manage_users', role=role)


# _____________________ Car Management____________________________________________________

@admin_or_staff_required
def manage_cars(request):
    messages_count = ContactMessage.objects.count()
    filter_type = request.GET.get('type', 'all')      
    filter_brand = request.GET.get('brand', 'all')     

    cars = Car.objects.all()
    featured_cars_count = cars.filter(featured=True).count()

    brands_dict = defaultdict(list)
    for car in cars:
        brand_name = car.brand if car.brand else "Other"
        brands_dict[brand_name].append(car)
    brands = [{"name": brand} for brand in brands_dict.keys()]

    if filter_type == 'featured':
        cars = cars.filter(featured=True)

    if filter_brand != 'all':
        matching_brand = next((b['name'] for b in brands if slugify(b['name']) == filter_brand), None)
        if matching_brand:
            cars = cars.filter(brand__iexact=matching_brand)

    context = {
        "cars": cars,
        "filter_type": filter_type,
        "filter_brand": filter_brand,
        "featured_cars_count": featured_cars_count,
        "brands": brands,
        "messages_count":messages_count,
    }

    return render(request, "admin/manage_cars.html", context)


@admin_or_staff_required
def add_car(request):
    CarImageFormSet = modelformset_factory(CarImage, form=CarImageForm, extra=1, can_delete=True)

    if request.method == 'POST':
        car_form = CarForm(request.POST, request.FILES)
        formset = CarImageFormSet(request.POST, request.FILES, queryset=CarImage.objects.none())

        if car_form.is_valid() and formset.is_valid():
            name = car_form.cleaned_data['name']
            brand = car_form.cleaned_data['brand']

            if Car.objects.filter(name__iexact=name, brand__iexact=brand).exists():
                messages.error(request, f"A car with name '{name}' and brand '{brand}' already exists.")
                return render(request, 'admin/add_car.html', {'car_form': car_form, 'formset': formset})
            car = car_form.save()

            for form in formset.cleaned_data:
                if form and not form.get('DELETE'):
                    image = form['image']
                    CarImage.objects.create(car=car, image=image)

            messages.success(request, "Car added successfully!")
            return redirect('manage_cars')

    else:
        car_form = CarForm()
        formset = CarImageFormSet(queryset=CarImage.objects.none())

    return render(request, 'admin/add_car.html', {'car_form': car_form, 'formset': formset})


@admin_or_staff_required
def edit_car(request, id):
    car = get_object_or_404(Car, id=id)

    if request.method == "POST":
     
        car_form = CarForm(request.POST, request.FILES, instance=car)
        if car_form.is_valid():
      
            car_form.save()

            for extra_image in car.extra_images.all():
                file = request.FILES.get(f'extra_image_{extra_image.id}')
                if file:
                    extra_image.image = file
                    extra_image.save()

            for key in request.FILES:
                if key.startswith('new_extra_image_'):
                    CarImage.objects.create(car=car, image=request.FILES[key])

            return redirect('manage_cars')
    else:
       
        car_form = CarForm(instance=car)

    return render(request, 'admin/edit_car.html', {'car': car, 'car_form': car_form})


@admin_only
def delete_car(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    if request.method == "POST":
        car.delete()
        messages.success(request, "Car deleted successfully.")
    return redirect('manage_cars')

@admin_only
def delete_selected_cars(request):
    if request.method == "POST":
        car_ids = request.POST.getlist('selected_cars') 
        if car_ids:
            Car.objects.filter(id__in=car_ids).delete()
            messages.success(request, f"{len(car_ids)} cars deleted successfully.")
        else:
            messages.warning(request, "No cars were selected.")
    return redirect('manage_cars')


# __________________ Booking and Customer_______________________________________________________

@admin_or_staff_required
def manage_bookings(request, customer_id=None):
    messages_count = ContactMessage.objects.count()
    today = timezone.localdate() 

    bookings = Booking.objects.filter(is_removed=False).order_by('-created_at')

    if customer_id:
        bookings = bookings.filter(user_id=customer_id)

    booking_type = request.GET.get('type')  
    status = request.GET.get('status')     
    today_flag = request.GET.get('today')  
    selected_date = request.GET.get('date') 

    if booking_type == 'car':
        bookings = bookings.filter(booking_type='book')
    elif booking_type == 'testdrive':
        bookings = bookings.filter(booking_type='test_drive')
    elif booking_type == 'service':
        bookings = bookings.filter(booking_type='service')


    if status:
       status_lower = status.lower()
       if status_lower == 'cancelled':
          bookings = bookings.filter(status__icontains='cancelled').exclude(status__iexact='paid')
       elif status_lower in ['approved', 'pending', 'completed']:
          bookings = bookings.filter(status__iexact=status_lower).exclude(status__iexact='paid')
    else:
        bookings = bookings.exclude(status__iexact='paid')


    if today_flag == 'true':
        today = timezone.localdate()
        bookings = bookings.filter(date=today)

    if selected_date:
        bookings = bookings.filter(date=selected_date)

    active_filter = None
    if 'type' in request.GET:
        active_filter = f"type_{request.GET.get('type')}"
    elif 'status' in request.GET:
          active_filter = f"status_{request.GET.get('status')}"
    elif 'today' in request.GET:
          active_filter = "today"
    elif 'date' in request.GET:
          active_filter = "date"

    pending_email_count = Booking.objects.filter(
       status="Completed",
       email_sent=False,
       booking_type__in=['book', 'service']
    ).count()

    
    filter_counts = {
        'type_all': Booking.objects.filter(is_removed=False).exclude(status__iexact='paid').count(),
        'type_car': Booking.objects.filter(booking_type='book', is_removed=False).exclude(status__iexact='paid').count(),
        'type_testdrive': Booking.objects.filter(booking_type='test_drive', is_removed=False).exclude(status__iexact='paid').count(),
        'type_service': Booking.objects.filter(booking_type='service', is_removed=False).exclude(status__iexact='paid').count(),

        'status_approved': Booking.objects.filter(status__iexact='approved', is_removed=False).exclude(status__iexact='paid').count(),
        'status_pending': Booking.objects.filter(status__iexact='pending', is_removed=False).exclude(status__iexact='paid').count(),
        'status_cancelled': Booking.objects.filter(status__icontains='cancelled', is_removed=False).exclude(status__iexact='paid').count(),
        'status_completed': Booking.objects.filter(status__iexact='completed', is_removed=False).exclude(status__iexact='paid').count(),

        'today': Booking.objects.filter(date=today, is_removed=False).exclude(status__iexact='paid').count(),
    }


    context = {
        'bookings': bookings,
        'customer': bookings.first().customer if customer_id and bookings.exists() else None,
        'filter_type': booking_type or 'all', 
        'status': status or 'all',   
        'active_filter': active_filter,   
        'today': today,       
        'pending_email_count': pending_email_count,  
        'filter_counts': filter_counts, 
        'messages_count': messages_count,
    }

    return render(request, 'admin/manage_bookings.html', context)

@admin_or_staff_required
def approve_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.booking_type == 'book' and booking.advance_payment <= 0:
        messages.error(request, f'Cannot approve booking {booking.id}. Advance payment not received.')
        return redirect('manage_bookings')

    booking.status = 'Approved'
    booking.save()

    if booking.booking_type == 'book' and booking.car:
        item_name = booking.car.name
    elif booking.booking_type == 'service' and booking.service:
        item_name = booking.service.name
    elif booking.booking_type == 'test_drive' and booking.car:
        item_name = booking.car.name
    else:
        item_name = "your booking"

    send_mail(
        subject='Your Booking is Approved!',
        message=f'Hello {booking.user.username}, your booking for {item_name} is approved.',
        from_email=django_settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.user.email],
        fail_silently=False,
    )

    messages.success(request, f'Booking {booking.id} approved and customer notified.')
    return redirect('manage_bookings')


@admin_or_staff_required
def complete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)


    if booking.booking_type == 'book' and booking.balance > 0:
        messages.error(request, "This car booking cannot be marked as completed because payment is not fully done.")
        return redirect('manage_bookings')

    if booking.booking_type == 'service' and not booking.is_fully_paid:
        messages.error(request, "This service booking cannot be marked as completed because payment is not fully done.")
        return redirect('manage_bookings')

    if booking.booking_type == 'test_drive' and booking.status != 'Approved':
        messages.error(request, "This test drive booking cannot be marked as completed because it is not approved yet.")
        return redirect('manage_bookings')

    booking.status = 'Completed'
    booking.save()
    messages.success(request, f"{booking.get_booking_type_display()} booking marked as completed.")
    return redirect('manage_bookings')


@admin_only
def delete_booking_admin(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)
        
        booking.is_active = False
        booking.status = 'Cancelled by Admin'
        booking.save()
        
        send_mail(
            subject=f'Booking #{booking.id} Cancelled',
            message=f'Hello {booking.user.username},\n\nYour booking "{booking}" has been cancelled by the admin.',
            from_email=None, 
            recipient_list=[booking.user.email],
            fail_silently=False,
        )
        
        messages.success(request, f'Booking {booking.id} has been cancelled and the user has been notified.')
        return redirect('manage_bookings')
    return JsonResponse({'error': 'Invalid request'}, status=400)


@admin_only
def remove_booking_row(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)
        booking.is_removed = True
        booking.save()
        messages.success(request, f'Booking {booking.id} removed from table.')
    return redirect(request.META.get('HTTP_REFERER', 'manage_bookings'))


@admin_only
def delete_removed_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, is_removed=True)
    booking.delete()
    messages.success(request, f"Removed booking #{booking.id} has been deleted.")
    return redirect('removed_bookings') 

@admin_only
def delete_all_removed_bookings(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_bookings')
        if selected_ids:
            bookings = Booking.objects.filter(id__in=selected_ids, is_removed=True)
            count = bookings.count()
            bookings.delete()
            messages.success(request, f"{count} removed booking(s) have been deleted.")
        else:
            messages.warning(request, "No bookings selected for deletion.")
    return redirect('removed_bookings')

@admin_or_staff_required
def booking_details(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, 'admin/booking_details.html', {'booking': booking})

@admin_or_staff_required
def add_booking(request):
    customers = User.objects.filter(role='customer')
    cars = Car.objects.all()
    services = Service.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user')
        booking_type = request.POST.get('booking_type')
        car_id = request.POST.get('car_select') or request.POST.get('car-select')
        service_id = request.POST.get('service_select') or request.POST.get('service-select')
        service_price = request.POST.get('service_price')
        date = request.POST.get('date')
        time = request.POST.get('time')
        from decimal import Decimal
        total_price = Decimal(request.POST.get('total_price') or request.POST.get('total_amount') or 0)
        advance_payment = Decimal(request.POST.get('advance_payment') or request.POST.get('advance') or 0)
        balance = Decimal(request.POST.get('balance') or (total_price - advance_payment))

        user = get_object_or_404(User, id=user_id)
        car = Car.objects.filter(id=car_id).first() if car_id else None
        service = Service.objects.filter(id=service_id).first() if service_id else None

        booking = Booking.objects.create(
            user=user,
            booking_type=booking_type,
            car=car,
            service=service,
            date=date,
            time=time,
            price=total_price,
            advance_payment=advance_payment,
            balance=balance,
            status='Pending',
            is_advance_paid=True if booking_type in ['book', 'service'] else False
        )

        # Send confirmation email
        subject = f"Booking Confirmation for Booking #{booking.id}"
        message = f"""
Hello {user.get_full_name() or user.username},

Your booking has been successfully created.

Booking Details:
- Booking Type: {booking.booking_type}
- Car: {booking.car.name if booking.car else 'N/A'}
- Service: {booking.service.name if booking.service else 'N/A'}
- Date: {booking.date}
- Time: {booking.time}
- Total Price: ₹{booking.price}
- Advance Payment: ₹{booking.advance_payment}
- Balance: ₹{booking.balance}

Thank you for choosing us!
"""
        send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, [user.email])

        messages.success(request, "Booking added and confirmation email sent!")
        return redirect('manage_bookings')

    context = {
        'customers': customers,
        'cars': cars,
        'services': services,
    }
    return render(request, 'admin/add_booking.html', context)

# _________________________Manage customer________________________________________________
@admin_or_staff_required
def manage_customers(request):
    messages_count = ContactMessage.objects.count()
    customers = User.objects.filter(is_staff=False, is_superuser=False, role='customer', is_removed=False)
    return render(request, "admin/manage_customers.html", {"customers": customers,"messages_count":messages_count,})

@admin_only
def delete_customer(request,customer_id):
    customer = get_object_or_404(User, id=customer_id)
    if request.method == "POST":
        customer.is_removed = True
        customer.save()
        messages.success(request,"Customer moved to trash.")
    return redirect(manage_customers)

@admin_or_staff_required
def add_customer_with_booking(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return redirect('add_customer_booking')

        customer = User.objects.create_user(
            username=username,
            email=email,
            password=User.objects.make_random_password(),
            role='customer'
        )
        customer.first_name = full_name.split()[0]
        customer.last_name = ' '.join(full_name.split()[1:])
        customer.save()

        booking_type = request.POST.get('booking_type')
        if booking_type:
            car_id = request.POST.get('car')
            service_id = request.POST.get('service')
            date = request.POST.get('date')
            time = request.POST.get('time')

            price = Decimal('0')
            advance = Decimal('0')
            if booking_type in ['book', 'test_drive'] and car_id:
                car = get_object_or_404(Car, id=car_id)
                price = car.price
                advance = price * Decimal('0.001')  # 0.1%
            elif booking_type == 'service' and service_id:
                service = get_object_or_404(Service, id=service_id)
                price = service.price
                advance = price * Decimal('0.10')  # 10%

            balance = price - advance

            booking = Booking.objects.create(
                user=customer,
                booking_type=booking_type,
                car_id=car_id if car_id else None,
                service_id=service_id if service_id else None,
                date=date,
                time=time,
                price=price,
                advance_payment=advance,
                balance=balance,
                is_advance_paid=(advance > 0),
                is_fully_paid=(balance == 0),
                status='Pending'
            )

            # Send confirmation email
            subject = f"Booking Confirmation #{booking.id}"
            message = f"""
Hello {customer.get_full_name() or customer.username},

Your booking has been successfully created.

Booking Details:
- Booking Type: {booking.booking_type}
- Car: {booking.car.name if booking.car else 'N/A'}
- Service: {booking.service.name if booking.service else 'N/A'}
- Date: {booking.date}
- Time: {booking.time}
- Total Price: ₹{booking.price}
- Advance Payment: ₹{booking.advance_payment}

Thank you for choosing us!
"""
            recipient_list = [customer.email]
            send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, recipient_list)

        messages.success(request, "Customer and booking added successfully!")
        return redirect('manage_customers')

    context = {
        'cars': Car.objects.all(),
        'services': Service.objects.all(),
    }
    return render(request, 'admin/add_customer_with_booking.html', context)

# ___________________________manage payments______________________________________________
@admin_or_staff_required
def manage_payments(request):
    messages_count = ContactMessage.objects.count()
   
    bookings = Booking.objects.filter(
        booking_type__in=['book', 'service'],
        advance_payment__gt=0,
        is_removed=False   
    ).select_related('user', 'car', 'service').order_by('-created_at')

    
    base_bookings = Booking.objects.filter(booking_type__in=['book', 'service'], is_removed=False)
    total_count = base_bookings.count()
    completed_count = base_bookings.filter(is_fully_paid=True).count()

   
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        start_date_obj = parse_date(start_date)
        if start_date_obj:
            bookings = bookings.filter(date__gte=start_date_obj)

    if end_date:
        end_date_obj = parse_date(end_date)
        if end_date_obj:
            bookings = bookings.filter(date__lte=end_date_obj)

    payments = []
    total_amount = total_advance = total_balance = Decimal('0.00')

    for b in bookings:
        if b.booking_type == 'book' and b.car:
            total_price = Decimal(b.car.price)
        elif b.booking_type == 'service' and b.service:
            total_price = Decimal(b.price) 
        else:
            total_price = Decimal('0.00')

        advance = Decimal(b.advance_payment) if b.advance_payment else Decimal('0.00')
        balance = Decimal(b.balance) if b.balance is not None else total_price - advance

        payments.append({
            "booking_id": b.id,
            "user": b.user,
            "car": b.car,
            "service": b.service,
            "total_amount": total_price,
            "advance": advance,
            "balance": balance,
            "date": b.date,
            "time": b.time,
            "status": b.status,
            "booked_on": b.created_at,

            "razorpay_order_id": b.razorpay_order_id,
            "razorpay_payment_id": b.razorpay_payment_id,
            "razorpay_signature": b.razorpay_signature,
            "booking_type": b.booking_type,
        })

        total_amount += total_price
        total_advance += advance
        total_balance += balance

    context = {
        "payments": payments,
        "total_amount": total_amount,
        "total_advance": total_advance,
        "total_balance": total_balance,
        "total_count": total_count,
        "completed_count": completed_count,
        "messages_count":messages_count,
    }

    return render(request, "admin/manage_payments.html", context)


@admin_or_staff_required
def completed_payments(request):
    bookings = Booking.objects.filter(booking_type__in=['book', 'service']).select_related('user', 'car', 'service')
  
    base_bookings = Booking.objects.filter(booking_type__in=['book', 'service'], is_removed=False)
    total_count = base_bookings.count()
    completed_count = base_bookings.filter(is_fully_paid=True).count()

    fully_paid = []
    for b in bookings:
        if b.booking_type == 'book' and b.car:
            total_price = Decimal(b.car.price)
        elif b.booking_type == 'service' and b.service:
            total_price = Decimal(b.price)
        else:
            total_price = Decimal('0.00')

        advance = Decimal(b.advance_payment or 0)
        balance = Decimal(b.balance or 0)

        if b.is_fully_paid or balance == 0:
            fully_paid.append({
                "booking_id": b.id,
                "user": b.user,
                "car": b.car,
                "service": b.service,
                "total_amount": total_price,
                "advance": advance,
                "balance": balance,
                "date": b.date,
                "time": b.time,
                "status": b.status,
                "booked_on": b.created_at,
                "razorpay_order_id": b.razorpay_order_id,
                "razorpay_payment_id": b.razorpay_payment_id,
                "razorpay_signature": b.razorpay_signature,
                "booking_type": b.booking_type,
            })

    context = {
        "payments": fully_paid,
        "total_amount": sum(p["total_amount"] for p in fully_paid),
        "total_advance": sum(p["advance"] for p in fully_paid),
        "total_balance": sum(p["balance"] for p in fully_paid),
        "total_count": total_count,
        "completed_count": completed_count,
    }

    return render(request, "admin/manage_payments.html", context)

@admin_only
def delete_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.is_removed = True 
    booking.save()
    messages.success(request, "Payment moved to trash bin.")
    return redirect('manage_payments')

@admin_only
def delete_multiple_payments(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_bookings')
        Booking.objects.filter(id__in=selected_ids).update(is_removed=True)
        messages.success(request, "Selected payments moved to trash.")
    return redirect(request.META.get('HTTP_REFERER', 'manage_payments'))

@admin_or_staff_required
def pay_full_amount(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == "POST":
        if booking.booking_type == 'book' and booking.car:
            total_price = Decimal(booking.car.price)
            item_name = booking.car.name
        elif booking.booking_type == 'service' and booking.service:
            total_price = Decimal(booking.price)
            item_name = booking.service.name
        else:
            messages.error(request, "Invalid booking.")
            return redirect('manage_payments')

        booking.balance = Decimal('0.00')
        booking.is_fully_paid = True
        booking.save()

        subject = f"Your Booking is Fully Paid"
        message = f"""
Hello {booking.user.username},

Your booking for "{item_name}" (Booking ID: {booking.id}) has now been fully paid.

Total Amount: ₹{total_price}
Advance Paid Earlier: ₹{booking.advance_payment}
Remaining Balance Paid: ₹0.00

Thank you!
"""
        send_mail(
            subject,
            message,
            django_settings.DEFAULT_FROM_EMAIL,
            [booking.user.email],
            fail_silently=False
        )

        messages.success(request, f"Booking ID {booking.id} marked as fully paid.")

    return redirect('manage_payments')

@admin_or_staff_required
def add_payment(request):
    customers = User.objects.filter(role='customer')
    cars = Car.objects.all()
    services = Service.objects.all()

    if request.method == "POST":
        user_id = request.POST.get('user')
        booking_type = request.POST.get('booking_type')
        car_id = request.POST.get('car-select') 
        service_id = request.POST.get('service-select')
        service_price = request.POST.get('service_price')  
        date = request.POST.get('date')
        time = request.POST.get('time')
        from decimal import Decimal
        total_price = Decimal(request.POST.get('total_amount', 0))
        advance_payment = Decimal(request.POST.get('advance', 0))
        balance = Decimal(request.POST.get('balance', total_price - advance_payment))

        user = get_object_or_404(User, id=user_id)
        car = Car.objects.filter(id=car_id).first() if car_id else None
        service = Service.objects.filter(id=service_id).first() if service_id else None

        
        booking = Booking.objects.create(
            user=user,
            booking_type=booking_type,
            car=car,
            service=service,
            date=date,
            time=time,
            price=total_price,
            advance_payment=advance_payment,
            balance=balance,
            status='Pending',
            is_advance_paid=True if booking_type in ['book', 'service'] else False
        )

        
        subject = f"Payment Confirmation for Booking #{booking.id}"
        message = f"""
Hello {user.get_full_name() or user.username},

Your payment has been recorded successfully.

Booking Details:
- Booking Type: {booking.booking_type}
- Car: {booking.car.name if booking.car else 'N/A'}
- Service: {booking.service.name if booking.service else 'N/A'}
- Date: {booking.date}
- Time: {booking.time}
- Total Price: ₹{booking.price}
- Advance Payment: ₹{booking.advance_payment}
- Balance: ₹{booking.balance}

Thank you for choosing us!
"""
        recipient_list = [user.email]
        send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, recipient_list)

        messages.success(request, "Payment added and confirmation email sent!")
        return redirect('manage_payments')

    context = {
        'customers': customers,
        'cars': cars,
        'services': services,
    }
    return render(request, 'admin/add_payment.html', context)


# ___________________________manage services______________________________________________
@admin_or_staff_required
def manage_services(request):
    messages_count = ContactMessage.objects.count()
    query = request.GET.get('q', '')
    if query:
        services = Service.objects.filter(name__icontains=query)
    else:
        services = Service.objects.all()
    return render(request, "admin/manage_services.html", {"services": services, "query": query,"messages_count":messages_count,})

@admin_or_staff_required
def add_service(request):
    if request.method == "POST":
        name = request.POST.get("name")
        category = request.POST.get("category")
        description = request.POST.get("description")
        price_min = request.POST.get("price_min")
        price_max = request.POST.get("price_max")
        duration = request.POST.get("duration")
        image = request.FILES.get("image")

 
        if Service.objects.filter(name__iexact=name, category__iexact=category).exists():
            messages.error(request, f"A service with name '{name}' in category '{category}' already exists.")
            return render(request, 'admin/add_service.html', {
                "name": name,
                "category": category,
                "description": description,
                "price_min": price_min,
                "price_max": price_max,
                "duration": duration
            })


        titles = request.POST.getlist("step_title[]")
        descriptions = request.POST.getlist("step_description[]")
        process_steps = [{"title": t, "description": d} for t, d in zip(titles, descriptions)]

   
        Service.objects.create(
            name=name,
            category=category,
            description=description,
            price_min=price_min,
            price_max=price_max,
            duration=duration,
            image=image,
            process_steps=process_steps
        )

        messages.success(request, "Service added successfully!")
        return redirect('manage_services')

    return render(request, 'admin/add_service.html')


@admin_or_staff_required
def edit_service(request, id):
    service = get_object_or_404(Service, id=id)

    if request.method == "POST":
        service.name = request.POST.get('name')
        service.category = request.POST.get('category')
        service.description = request.POST.get('description')
        service.price_min = Decimal(request.POST.get('price_min')) if request.POST.get('price_min') else None
        service.price_max = Decimal(request.POST.get('price_max')) if request.POST.get('price_max') else None
        service.duration = request.POST.get('duration')
        if request.FILES.get('image'):
            service.image = request.FILES.get('image')

        titles = request.POST.getlist('step_title[]')
        descriptions = request.POST.getlist('step_description[]')
        steps = []

        for i in range(len(titles)):
            step = {
                "title": titles[i],
                "description": descriptions[i],
            }
            steps.append(step)

        service.process_steps = steps  
        service.save()

        return redirect('manage_services')

    return render(request, 'admin/edit_service.html', {'service': service})

@admin_only
def delete_service(request, id):
    service = get_object_or_404(Service, id=id)
    if request.method == "POST":
        service.delete()
        return redirect('manage_services')
    return render(request, 'admin/service_confirm_delete.html', {'service': service})

@admin_or_staff_required
def view_service(request, id):
    service = get_object_or_404(Service, id=id)
    return render(request, 'admin/view_service.html', {'service': service})


# _________________________________________________________________________
@admin_or_staff_required
def reports(request):
    messages_count = ContactMessage.objects.count()
    filter_type = request.GET.get('filter', 'all')

    last_data = [] 

    if filter_type in ["bookings", "payments", "test_drive", "services"]:
        qs = Booking.objects.filter(is_removed=False).select_related('user', 'car', 'service')

        if filter_type == "bookings":
           qs = qs.filter(booking_type="book")  

        elif filter_type == "payments":
           qs = qs.filter(Q(advance_payment__gt=0) | Q(balance__gt=0))

        elif filter_type == "services":
           qs = qs.filter(booking_type="service")

        elif filter_type == "test_drive":
           qs = qs.filter(booking_type="test_drive")

        last_data = qs.order_by('-created_at')

    elif filter_type in ["customers", "staff"]:
        if filter_type == "customers":
            last_data = User.objects.filter(role='customer').order_by('-date_joined')
        else: 
            last_data = User.objects.filter(role__in=['staff', 'admin']).order_by('-date_joined')

    elif filter_type == "all":
        last_data = Booking.objects.filter(is_removed=False).order_by('-created_at')

    total_cars = Car.objects.count()
    total_services = Service.objects.count()
    total_staff = User.objects.filter(role='staff').count()
    total_customers = User.objects.filter(role='customer').count()
    total_bookings = Booking.objects.filter(is_removed=False).count()

    payments = Booking.objects.filter(is_removed=False).aggregate(
        adv=Sum('advance_payment'),
        bal=Sum('balance')
    )

    total_revenue = sum([
    float(payments.get('adv') or 0),
    float(payments.get('bal') or 0)
     ])


    daily_qs = Booking.objects.filter(date__isnull=False, is_removed=False).values('date').annotate(
        count=Count('id'),
        advance_total=Sum('advance_payment'),
        balance_total=Sum('balance'),
    ).order_by('date')

    daily_bookings_data = {
        'labels': [b['date'].strftime("%d %b %Y") for b in daily_qs],
        'counts': [b['count'] for b in daily_qs],
        'advance': [float(b['advance_total'] or 0) for b in daily_qs],
        'balance': [float(b['balance_total'] or 0) for b in daily_qs],
    }

    context = {
        'total_cars': total_cars,
        'total_services': total_services,
        'total_staff': total_staff,
        'total_customers': total_customers,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'daily_bookings_data': daily_bookings_data,
        'last_data': last_data,
        'current_filter': filter_type,
        "messages_count":messages_count,
    }

    return render(request, 'admin/reports.html', context)

@admin_or_staff_required
def removed_items(request):
    filter_type = request.GET.get("filter", "bookings")
    data = []

    counts = {
        "bookings": Booking.objects.filter(is_removed=True,is_refunded=False).count(),
        "booked_parts": BookedSparePart.objects.filter(is_removed=True,is_refunded=False).count(),
        "customers": User.objects.filter(role='customer', is_removed=True).count(),
        "staff": User.objects.filter(is_staff=True, is_superuser=False, is_removed=True).count(),
        "admin": User.objects.filter(is_superuser=True, is_removed=True).count(),
        "payments": Booking.objects.filter(
            Q(advance_payment__gt=0) | Q(balance__gt=0),
            is_removed=True
        ).count(),
        "refunds": Booking.objects.filter(is_refunded=True, is_removed=True).count() +
           BookedSparePart.objects.filter(is_refunded=True, is_removed=True).count(),

    }
     
    total_trash = sum(counts.values())
    
    if filter_type == "bookings":
        data = Booking.objects.filter(is_removed=True,is_refunded=False).order_by('-created_at')

    elif filter_type == "booked_parts": 
        data = BookedSparePart.objects.filter(is_removed=True,is_refunded=False).select_related('part', 'user').order_by('-created_at')

    elif filter_type == "customers":
        data = User.objects.filter(
            role='customer',
            is_removed=True
        ).order_by('-date_joined')

    elif filter_type == "staff":
        data = User.objects.filter(
            is_staff=True,
            is_superuser=False,
            is_removed=True
        ).order_by('-date_joined')

    elif filter_type == "admin":
        data = User.objects.filter(
            is_superuser=True,
            is_removed=True
        ).order_by('-date_joined')

    elif filter_type == "payments":
        removed_payments = Booking.objects.filter(
            Q(advance_payment__gt=0) | Q(balance__gt=0),
            is_removed=True
        ).select_related('user', 'car', 'service').order_by('-created_at')

        for b in removed_payments:
            if b.booking_type == "book" and b.car:
                total_price = Decimal(b.car.price)
            elif b.booking_type == "service" and b.service:
                total_price = Decimal(b.price)
            else:
                total_price = Decimal("0.00")

            advance = Decimal(b.advance_payment or 0)
            balance = Decimal(b.balance) if b.balance is not None else total_price - advance

            data.append({
                "id": b.id,
                "car": b.car,
                "service": b.service,
                "username": b.user.username,
                "total_amount": total_price,
                "advance_payment": advance,
                "balance": balance,
                "status": b.status,
            })

    elif filter_type == "refunds":
        booking_refunds = Booking.objects.filter(is_refunded=True, is_removed=True).select_related('user', 'car', 'service').order_by('-created_at')

        spare_refunds = BookedSparePart.objects.filter(is_refunded=True, is_removed=True).select_related('user', 'part').order_by('-created_at')

        data = []

        for b in booking_refunds:
          data.append({
            "type": "Booking",
            "id": b.id,
            "user": b.user.username,
            "item": b.car.name if b.car else (b.service.name if b.service else f"Booking #{b.id}"),
            "amount": b.advance_payment,
            "date": b.created_at,
            "status": "Refunded",
        })

        for s in spare_refunds:
          data.append({
            "type": "Spare Part",
            "id": s.id,
            "user": s.user.username,
            "item": s.part.name,
            "amount": s.amount,
            "date": s.created_at,
            "status": "Refunded",
        })


        data = sorted(data, key=lambda x: x["date"], reverse=True)


    return render(request, 'admin/removed_items.html', {
        "filter_type": filter_type,
        "data": data,
        "counts": counts,  
        "total_trash": total_trash, 
    })


@admin_only
def bulk_removed_action(request):
    if request.method == 'POST':
        item_ids = request.POST.getlist('selected_ids')
        filter_type = request.POST.get('filter_type')
        action = request.POST.get('action')

        if not item_ids:
            messages.warning(request, "No items selected.")
            return redirect('removed_items')

        if filter_type == "bookings":
            qs = Booking.objects.filter(id__in=item_ids)
        elif filter_type == "booked_parts":
            qs = BookedSparePart.objects.filter(id__in=item_ids)
        elif filter_type == "customers":
            qs = User.objects.filter(id__in=item_ids)
        elif filter_type == "staff":
            qs = User.objects.filter(id__in=item_ids)
        elif filter_type == "admin":
            qs = User.objects.filter(id__in=item_ids)
        elif filter_type == "payments":
            qs = Booking.objects.filter(
               Q(advance_payment__gt=0) | Q(balance__gt=0),
               is_removed=True )
        else:
            qs = None

        if qs:
            if action == "restore":
                if filter_type in ["bookings", "booked_parts"]:
                    qs.update(is_removed=False)
                else:
                    qs.update(is_active=True)
                messages.success(request, f"{len(item_ids)} items restored.")

            elif action == "delete":
                qs.delete()
                messages.success(request, f"{len(item_ids)} items deleted permanently.")

    return redirect('removed_items')


# ________________________ Admin profile_________________________________________________

@admin_or_staff_required
def admin_profile(request):
    messages_count = ContactMessage.objects.count()
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = AdminProfileForm(request.POST, instance=user)
        profile_form = AdminProfileImageForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('admin_dashboard')
    else:
        user_form = AdminProfileForm(instance=user)
        profile_form = AdminProfileImageForm(instance=profile)

    return render(request, 'admin/admin_dashboard.html', {
        "show_profile": True,
        "user_form": user_form,
        "profile_form": profile_form,
        "messages_count":messages_count,
    })


# _________________________________________________________________________

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()


# ________________ Pages _________________________________________________________

def home(request):
    brands = Car.objects.values_list('brand', flat=True).distinct()
    featured_cars = Car.objects.filter(featured=True)[:5]
    all_cars = Car.objects.all()

    is_subscribed = False
    if request.user.is_authenticated:
        subscriber = NewsletterSubscriber.objects.filter(
            email=request.user.email,
            is_subscribed=True
        ).first()
        if subscriber:
            is_subscribed = True

    return render(request, "accounts/home.html", {
        "brands": brands,
        "featured_cars": featured_cars,
        "cars": all_cars,
        "is_subscribed": is_subscribed
    })

def car_list(request):
    cars = Car.objects.all().order_by('?')
    query = request.GET.get("q", "").strip()

    if query:
        cars = cars.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query) |
            Q(name__icontains=query.lower()) |
            Q(category__icontains=query)
        )

    user_wishlist = []
    if request.user.is_authenticated: 
        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('car_id', flat=True)

    return render(request, "accounts/car_list.html", {
        "cars": cars,
        "query": query,
        "user_wishlist": list(user_wishlist),
        "no_results": not cars.exists()
    })


def car_brand_list(request, brand_name):
    cars = Car.objects.filter(brand__iexact=brand_name)

    if request.user.is_authenticated:
        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('car_id', flat=True)
    else:
        user_wishlist = []  

    return render(request, 'accounts/car_list.html', { 
        'cars': cars,
        'brand_name': brand_name,
        'user_wishlist': list(user_wishlist)  
    })

@login_required
def toggle_wishlist(request, car_id):
    if request.method == 'POST':
        car = Car.objects.get(id=car_id)
        wishlist_item = Wishlist.objects.filter(user=request.user, car=car).first()
        if wishlist_item:
            wishlist_item.delete()
            return JsonResponse({'status': 'removed'})
        else:
            Wishlist.objects.create(user=request.user, car=car)
            return JsonResponse({'status': 'added'})
    return JsonResponse({'status': 'error'})

def car_details(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    extra_images = car.extra_images.all()

    user_wishlist = []
    if request.user.is_authenticated:
        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('car_id', flat=True)

    similar_cars = Car.objects.filter(category=car.category).exclude(id=car.id)[:4]

    return render(request, 'accounts/car_details.html', {
        'car': car,
        'extra_images': extra_images,
        'user_wishlist': user_wishlist,
        'similar_cars': similar_cars,
    })


def about(request):
    approved_reviews = Review.objects.filter(status='Accepted') \
                                     .select_related('user__profile') \
                                     .order_by('-created_at')
    context = {
        'approved_reviews': approved_reviews,
    }
    return render(request, "accounts/about.html", context)

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        message_text = request.POST.get("message")
        ContactMessage.objects.create(
            name=name,
            email=email,
            phone=phone,
            message=message_text
        )

        messages.success(request, "Your message has been sent successfully!")
        return redirect("contact")  

    return render(request, "accounts/contact.html")

def autocomplete_search(request):
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        cars = Car.objects.filter(
            Q(name__icontains=query) | Q(brand__icontains=query)
        ).values('id', 'brand', 'name')[:5]  
        for car in cars:
            results.append({
                'type': 'Car',                         
                'id': car['id'],                      
                'label': f"{car['brand']} {car['name']}", 
                'value': car['name']  ,
                
            })

    return JsonResponse(results, safe=False)


# ___________________________Profile ______________________________________________

@login_required
def profile(request, user_id=None):
    if user_id:
        customer = get_object_or_404(User, id=user_id)
    else:
        customer = request.user

    # Password change
    if request.method == 'POST':
        form = PasswordChangeForm(customer, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated successfully!", extra_tags='password-success')
            return redirect('/profile/?tab=password')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error, extra_tags='password-error')
            return redirect('/profile/?tab=password')
    else:
        form = PasswordChangeForm(customer)

    today = date.today()

    wishlist_items = Wishlist.objects.filter(user=customer).select_related('car')
    reviewed_booking_ids = Review.objects.filter(user=customer).values_list('booking_id', flat=True)
    reviewed_spare_ids = Review.objects.filter(user=customer).values_list('spare_booking_id', flat=True)

    # Status filter
    status_filter = request.GET.get('status', 'all').lower()
    active_filter = status_filter

    # Base queryset
    bookings = Booking.objects.filter(user=customer,is_removed=False).select_related('service').order_by('-created_at')

    # Update completed bookings automatically
    for booking in bookings:
        if booking.status.lower() == 'approved' and booking.date and booking.date < today:
            booking.status = 'Completed'
            booking.save(update_fields=['status'])

    # Apply status filter
    if status_filter == 'pending':
        bookings = bookings.filter(status='Pending')
    elif status_filter == 'approved':
        bookings = bookings.filter(status='Approved')
    elif status_filter == 'completed':
        bookings = bookings.filter(status='Completed')
    elif status_filter == 'cancelled':
        bookings = bookings.filter(Q(status='Cancelled by Admin') | Q(status='Cancelled') | Q(is_active=False))

    # Spare bookings
    spare_bookings = BookedSparePart.objects.filter(
    user=customer,
    is_removed=False
     ).filter(
    Q(deleted_by_user=False) | Q(status='Cancelled by User')
    ).order_by('-created_at')

    if status_filter == 'pending':
       spare_bookings = spare_bookings.filter(status__iexact='booked')
    elif status_filter == 'completed':
       spare_bookings = spare_bookings.filter(status__iexact='delivered')
    elif status_filter == 'cancelled':
       spare_bookings = spare_bookings.filter(status='Cancelled by User')

    return render(request, 'accounts/profile.html', {
        'customer': customer,
        'bookings': bookings,
        'spare_bookings': spare_bookings,
        'wishlist_items': wishlist_items,
        'form': form,
        'active_tab': request.GET.get('tab', 'bookings'),
        'active_filter': active_filter,
        'reviewed_booking_ids': reviewed_booking_ids,
        'reviewed_spare_ids': reviewed_spare_ids,
    })


@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        profile_form = AdminProfileForm(request.POST, instance=user)
        image_form = AdminProfileImageForm(request.POST, request.FILES, instance=user.profile)
        if profile_form.is_valid() and image_form.is_valid():
            profile_form.save()
            image_form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('profile')
    else:
        profile_form = AdminProfileForm(instance=user)
        image_form = AdminProfileImageForm(instance=user.profile)

    context = {'profile_form': profile_form, 'image_form': image_form}
    return render(request, 'accounts/edit_profile.html', context)


@login_required
def remove_booking_user(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    booking.is_removed = True  # soft delete
    booking.save(update_fields=['is_removed'])
    messages.success(request, "Booking removed from your profile.")
    return redirect('profile')

@login_required
def remove_spare_booking_user(request, booking_id):
    spare_booking = get_object_or_404(BookedSparePart, id=booking_id, user=request.user)
    
    if not spare_booking.is_removed:
        spare_booking.is_removed = True  # soft delete
        spare_booking.save(update_fields=['is_removed'])
        messages.success(request, "Spare part booking removed from your profile.")
    else:
        messages.info(request, "This spare part booking was already removed.")

    return redirect('profile')

# ____________________ Services _____________________________________________________

def services_list(request):
    services = Service.objects.all().order_by('name')
    
    grouped_services = defaultdict(list)
    for service in services:
        grouped_services[service.category or 'Uncategorized'].append(service)
    
    return render(request, 'services/services_list.html', {'grouped_services': dict(grouped_services)})


def services_by_category(request, category_name):
    if category_name == "Uncategorized":
        services = Service.objects.filter(category__isnull=True)
    else:
        services = Service.objects.filter(category=category_name)

    grouped_services = defaultdict(list)
    for service in services:
        grouped_services[service.category or 'Uncategorized'].append(service)

    return render(request, 'services/services_list.html', {'grouped_services': dict(grouped_services)})

def service_detail(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    return render(request, 'services/service_detail.html', {'service': service})

def services_context(request):
    services = Service.objects.all().order_by('name')
    grouped_services = defaultdict(list)
    
    for service in services:
        grouped_services[service.category or 'Uncategorized'].append(service)
    
    return {'grouped_services': dict(grouped_services)}


@login_required
def book_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    available_times = ['10:00', '11:00', '12:00', '14:00', '15:00']
    selected_price = request.GET.get('selected_price')  
    if not selected_price:
        selected_price = service.price_min
    selected_price = Decimal(selected_price)
    advance_payment = (selected_price * Decimal('0.10')).quantize(Decimal('0.01'))
    client = razorpay.Client(auth=(django_settings.RAZORPAY_KEY_ID, django_settings.RAZORPAY_KEY_SECRET))
    razorpay_order = client.order.create({
        "amount": int(advance_payment * 100), 
        "currency": "INR",
        "payment_capture": 1
    })

    return render(request, 'accounts/book_service.html', {
        'service': service,
        'available_times': available_times,
        'today': date.today(),
        'razorpay_key_id': django_settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': razorpay_order['id'],
        'selected_price': selected_price,
        'advance_payment': advance_payment,
        'type': 'service'
    })


@login_required
def verify_service_payment(request):
    if request.method != "POST":
        return JsonResponse({"status": "failed", "message": "Invalid request method"})

    client = razorpay.Client(
        auth=(django_settings.RAZORPAY_KEY_ID, django_settings.RAZORPAY_KEY_SECRET)
    )

    data = request.POST
    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")
    service_id = data.get("service_id")
    selected_price = Decimal(data.get("selected_price"))
    name = data.get("name")
    email = data.get("email")
    booking_date = data.get("date")
    booking_time = data.get("time")
    phone = data.get("phone")

    if not all([order_id, payment_id, signature, service_id, selected_price, name, email, booking_date, booking_time]):
        return JsonResponse({"status": "failed", "message": "Missing required parameters"})

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"status": "failed", "message": "Signature verification failed"})

    service = get_object_or_404(Service, id=service_id)
    advance_payment = (selected_price * Decimal('0.10')).quantize(Decimal('0.01'))
    balance = selected_price - advance_payment

    booking = Booking.objects.create(
        user=request.user,
        service=service,
        booking_type='service',
        name=name,
        email=email,
        phone=phone,
        date=booking_date,
        time=booking_time,
        price=selected_price,
        advance_payment=advance_payment,
        balance=balance,
        created_at=timezone.now(),
        duration=service.duration,
        is_advance_paid=True,
        is_fully_paid=False,
        status='Pending',
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature
    )

    # Send confirmation email
    subject = f"Service Booking Confirmation #{booking.id}"
    message = f"""
Hello {name},

Your service booking has been successfully created.

Booking Details:
- Service: {service.name}
- Date: {booking.date}
- Time: {booking.time}
- Total Price: ₹{booking.price}
- Advance Payment: ₹{booking.advance_payment}

Thank you for choosing our service!
"""
    recipient_list = [email]
    send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, recipient_list)

    return JsonResponse({"status": "success", "message": "Booking created successfully"})

@login_required
def create_service_order(request):
    if request.method == "POST":
        service_id = request.POST.get('service_id')
        selected_price = Decimal(request.POST.get('selected_price'))
        advance_payment = (selected_price * Decimal('0.10')).quantize(Decimal('0.01'))

        service = get_object_or_404(Service, id=service_id)

        client = razorpay.Client(auth=(django_settings.RAZORPAY_KEY_ID, django_settings.RAZORPAY_KEY_SECRET))
        order = client.order.create({
            "amount": int(advance_payment * 100),
            "currency": "INR",
            "payment_capture": 1
        })
        return JsonResponse({"order_id": order["id"]})
    return JsonResponse({"error": "Invalid request"}, status=400)

# _________________________ Customer Details________________________________________________
@admin_only
def customer_profile(request, user_id):
    messages_count = ContactMessage.objects.count()

    if not request.user.is_superuser:
        return redirect('admin_dashboard') 

    customer = get_object_or_404(User, id=user_id)

    bookings = customer.bookings.all().order_by('-created_at')
    test_drives = bookings.filter(booking_type='test_drive')
    rents = bookings.filter(booking_type='rent')
    purchases = bookings.filter(booking_type='book')
    wishlist = getattr(customer, 'wishlist', None)

    return render(request, 'customers/customer_profile.html', {
        'customer': customer,
        'bookings': bookings,
        'test_drives': test_drives,
        'rents': rents,
        'purchases': purchases,
        'wishlist': wishlist,
        'messages_count':messages_count
    })


@admin_only
def customer_bookings(request, id):
    messages_count = ContactMessage.objects.count()
    customer = get_object_or_404(User, id=id)
    bookings = Booking.objects.filter(user=customer).order_by('-created_at')
    return render(request, 'customers/customer_bookings.html', {'customer': customer, 'bookings': bookings,'messages_count':messages_count})

# ________________User Bookings_________________________________________________________

@login_required
def book_car_action(request, car_id, booking_type):
    car = get_object_or_404(Car, id=car_id)
    available_times = ['10:00', '11:00', '12:00', '14:00', '15:00']

    if booking_type.lower() == 'book':
        advance_payment = (car.price * Decimal('0.001')).quantize(Decimal('0.001'))
        balance = car.price - advance_payment

        client = razorpay.Client(
            auth=(django_settings.RAZORPAY_KEY_ID, django_settings.RAZORPAY_KEY_SECRET)
        )

        try:
            razorpay_order = client.order.create({
                "amount": int(advance_payment * 100),
                "currency": "INR",
                "payment_capture": 1
            })
        except Exception as e:
            messages.error(request, f"Failed to create payment order: {str(e)}")
            return redirect('car_list')

      
        return render(request, 'accounts/book_car.html', {
            'car': car,
            'type': booking_type,
            'today': date.today(),
            'available_times': available_times,
            'advance_payment': advance_payment,
            'balance': balance,
            'total_amount': car.price,
            'razorpay_key_id': django_settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': razorpay_order.get('id'),
            'amount': int(advance_payment * 100),
        })


    else:
        if request.method == 'POST':
            form = BookingForm(request.POST, booking_type=booking_type)
            if form.is_valid():
                booking = form.save(commit=False)
                booking.user = request.user
                booking.car = car
                booking.booking_type = booking_type
                booking.save()
                messages.success(request, "Test drive booked successfully!")
                return redirect('car_list')
            else:
                messages.error(request, "Please select valid date and time.")
        else:
            form = BookingForm(booking_type=booking_type)

        return render(request, 'accounts/book_test_drive.html', {
            'form': form,
            'car': car,
            'type': booking_type,
            'today': date.today(),
            'available_times': available_times,
        })

@login_required
def verify_payment(request):
    if request.method != "POST":
        return JsonResponse({"status": "failed", "message": "Invalid request method"})

    client = razorpay.Client(
        auth=(django_settings.RAZORPAY_KEY_ID, django_settings.RAZORPAY_KEY_SECRET)
    )

    data = request.POST
    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")
    car_id = data.get("car_id")
    booking_date = data.get("date")
    booking_time = data.get("time")
    booking_type = data.get("booking_type", "book")
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    pickup_location = data.get("pickup_location")
    notes = data.get("notes")

    if not all([order_id, payment_id, signature, car_id, booking_date, booking_time]):
        return JsonResponse({"status": "failed", "message": "Missing required parameters"})

    
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"status": "failed", "message": "Signature verification failed"})

    
    car = get_object_or_404(Car, id=car_id)
    total_price = car.price

    
    advance_payment = (total_price * Decimal('0.001')).quantize(Decimal('0.001'))
    balance = total_price - advance_payment

   
    booking = Booking.objects.create(
        user=request.user,
        car=car,
        booking_type=booking_type,
        name=name,
        email=email,
        phone=phone,
        date=booking_date,
        time=booking_time,
        pickup_location=pickup_location,
        notes=notes,
        advance_payment=advance_payment,
        price=total_price,
        balance=balance,
        is_advance_paid=True,
        is_fully_paid=False,
        status='Pending', 
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature
    )

   
    subject = "Payment Successful for Your Booking"
    message = f"""
Hello {booking.user.username},

Your payment for booking the car "{booking.car.name}" has been successfully received.

Booking Details:
Date: {booking.date}
Time: {booking.time}
Pickup Location: {pickup_location or 'Not provided'}
Amount Paid: ₹{advance_payment}
Remaining Balance: ₹{balance}

Thank you for choosing us!
"""
    send_mail(
        subject,
        message,
        django_settings.DEFAULT_FROM_EMAIL,
        [booking.email],
        fail_silently=False
    )

    return JsonResponse({"status": "success", "message": "Payment verified and booking created"})

# ________________review_________________________________________________________

@admin_or_staff_required
def admin_contact_messages(request):
    tab = request.GET.get('tab', 'messages')

    messages_count = ContactMessage.objects.count()
    reviews_count = Review.objects.count()

    if tab == 'reviews':
        reviews = Review.objects.all().order_by('-created_at')
        context = {
            'active_tab': 'reviews',
            'reviews': reviews,
            'messages_count': messages_count,
            'reviews_count': reviews_count,
        }
    else:
        messages_list = ContactMessage.objects.all().order_by('-created_at')
        context = {
            'active_tab': 'messages',
            'messages_list': messages_list,
            'messages_count': messages_count,
            'reviews_count': reviews_count,
        }

    return render(request, 'admin/admin_contact_messages.html', context)


# contact msg
@admin_only
def delete_message(request, pk):
    message_obj = get_object_or_404(ContactMessage, pk=pk)
    message_obj.delete()
    messages.success(request, 'Message deleted successfully.')
    return redirect('admin_contact_messages')


# customer side
@login_required
def submit_review(request, booking_id):
    booking = Booking.objects.get(id=booking_id, user=request.user)

    if Review.objects.filter(user=request.user, booking=booking).exists():
        messages.info(request, "You have already reviewed this booking.")
        return redirect('profile')

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        Review.objects.create(
            user=request.user,
            booking=booking,
            rating=rating,
            comment=comment
        )

        messages.success(request, "Thanks for your review!")
        return redirect('profile')

    return redirect('profile')


@login_required
def submit_spare_review(request, booking_id):
    spare_booking = get_object_or_404(BookedSparePart, id=booking_id, user=request.user)

    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment", "")

        Review.objects.create(
            user=request.user,
            spare_booking=spare_booking,
            rating=rating,
            comment=comment,
        )

        messages.success(request, "Thanks for your review!")
        return redirect('profile')
    
    return redirect('/profile/?status=completed&tab=spare')


# review admin side
@admin_or_staff_required
def accept_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.status = "Accepted"
    review.is_approved = True
    review.save()
    messages.success(request, "Review accepted successfully!")
    return redirect('/dashboard/admin/contact-messages/?tab=reviews')

@admin_or_staff_required
def reject_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.status = "Rejected"
    review.is_approved = False
    review.save()
    messages.error(request, "Review rejected.")
    return redirect('/dashboard/admin/contact-messages/?tab=reviews')

@admin_only
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, "Review deleted successfully!")
    return redirect('/dashboard/admin/contact-messages/?tab=reviews')


@admin_or_staff_required
def send_all_due_emails(request):

    
    completed_bookings = Booking.objects.filter(
        status="Completed",
        email_sent=False,
        booking_type__in=['book', 'service']
    ).select_related('user')

    if not completed_bookings:
        messages.warning(request, "No pending service reminder emails found.")
        return redirect('manage_bookings')

    count = 0

    for booking in completed_bookings:
        user = booking.user

        if not user.email:
            continue

        
        if booking.booking_type == "book":
            due_date = booking.created_at + timedelta(days=90)
            subject = "Your First Service Due Date"
            message = f"""
Hi {user.get_full_name() or user.username},

Congratulations on your new car purchase!

Your FIRST service is due on: {due_date.strftime('%d %B %Y')}

Regards,
Your Service Team
"""
        elif booking.booking_type == "service":
            due_date = booking.created_at + timedelta(days=180)
            subject = "Your Next Service Due Date"
            message = f"""
Hi {user.get_full_name() or user.username},

Thank you for completing your recent service!

Your NEXT service is due on: {due_date.strftime('%d %B %Y')}

Regards,
Your Service Team
"""

        send_mail(
            subject,
            message,
            'yourcompany@example.com',
            [user.email],
            fail_silently=False,
        )

        booking.email_sent = True
        booking.email_sent_at = timezone.now()
        booking.save()
        count += 1

    messages.success(request, f"Emails successfully sent to {count} customers.")
    return redirect('manage_bookings')

# ________________spare parts_________________________________________________________

@admin_or_staff_required
def manage_spare_parts(request):
    messages_count = ContactMessage.objects.count()
    search_query = request.GET.get('search', '')
    parts = SparePart.objects.all()

    if search_query:
        parts = parts.filter(
            Q(name__icontains=search_query) |
            Q(category__icontains=search_query)
        )

    if request.method == 'POST' and 'add_part' in request.POST:
        name = request.POST.get('name')
        category = request.POST.get('category')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        description = request.POST.get('description', '')
        available = 'available' in request.POST

        
        if SparePart.objects.filter(name__iexact=name, category__iexact=category).exists():
            messages.error(request, f"A spare part with name '{name}' in category '{category}' already exists.")
            return render(request, 'admin/manage_spare_parts.html', {
                'parts': parts,
                'categories': SparePart.CATEGORY_CHOICES,
                'messages_count': messages_count,
                'search_query': search_query,
                'name': name,
                'category': category,
                'price': price,
                'stock': stock,
                'description': description,
                'available': available
            })

        if name and category and price and stock:
            SparePart.objects.create(
                name=name,
                category=category,
                price=price,
                stock=stock,
                description=description,
                available=available
            )
            messages.success(request, 'Spare part added successfully.')
            return redirect('manage_spare_parts')
        else:
            messages.error(request, 'Please fill all required fields.')

    return render(request, 'admin/manage_spare_parts.html', {
        'parts': parts,
        'categories': SparePart.CATEGORY_CHOICES,
        'messages_count': messages_count,
        'search_query': search_query,
    })


@admin_or_staff_required
def edit_spare_part(request, part_id):
    part = get_object_or_404(SparePart, id=part_id)

    if request.method == 'POST':
        part.name = request.POST.get('name')
        part.category = request.POST.get('category')
        part.price = request.POST.get('price')
        part.stock = request.POST.get('stock')
        part.description = request.POST.get('description', '')
        part.available = 'available' in request.POST 
        part.save()
        messages.success(request, 'Spare part updated successfully.')
        return redirect('manage_spare_parts')

    return render(request, 'admin/edit_spare_part.html', {
        'part': part,
        'categories': SparePart.CATEGORY_CHOICES
    })

@admin_only
def delete_spare_part(request, part_id):
    part = get_object_or_404(SparePart, id=part_id)
    part.delete()
    messages.success(request, 'Spare part deleted successfully.')
    return redirect('manage_spare_parts')

@admin_only
def bulk_delete_spare_parts(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_parts')
        if selected_ids:
            SparePart.objects.filter(id__in=selected_ids).delete()
            messages.success(request, 'Selected spare parts deleted successfully.')
        else:
            messages.error(request, 'No spare parts selected.')
    return redirect('manage_spare_parts')


@admin_or_staff_required
def booked_spare_parts(request):
    """
    View to display all booked spare parts.
    """
    messages_count = ContactMessage.objects.count()
    booked_parts = BookedSparePart.objects.select_related('part', 'user').filter(is_removed=False).order_by('-id')

    search_query = request.GET.get('search', '')
    if search_query:
        booked_parts = booked_parts.filter(
            part__name__icontains=search_query
        )

    total_collected = booked_parts.aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'admin/booked_spare_parts.html', {
        'booked_parts': booked_parts,
        'search_query': search_query,
        'messages_count': messages_count,
        'total_collected': total_collected
    })


@admin_or_staff_required
@require_POST
def mark_delivered(request, booking_id):
    booking = get_object_or_404(BookedSparePart, id=booking_id)
    if booking.status != 'delivered':
        booking.status = 'delivered'
        
        if booking.payment_method == 'cod':
            booking.is_paid = True
        
        booking.save()
        messages.success(request, f"{booking.part.name} marked as delivered!")

       
        if booking.email:
            subject = f"Booking Delivered: {booking.part.name}"
            message = (
                f"Hi {booking.customer_name},\n\n"
                f"Your booking for '{booking.part.name}' has been successfully delivered.\n"
                f"Quantity: {booking.quantity}\n\n"
                "Thank you for choosing our service!"
            )
            send_mail(
                subject,
                message,
                django_settings.DEFAULT_FROM_EMAIL,
                [booking.email],
                fail_silently=True
            )

    else:
        messages.info(request, f"{booking.part.name} is already delivered.")
    return redirect('booked_spare_parts')

@admin_only
@require_POST
def delete_booking(request, booking_id):
    booking = get_object_or_404(BookedSparePart, id=booking_id)
    if not booking.is_removed:
        booking.is_removed = True
        booking.save()
        messages.success(request, f"Booking for {booking.part.name} moved to trash!")
    else:
        messages.info(request, f"Booking for {booking.part.name} is already in trash.")
    return redirect('booked_spare_parts')


# ________________spare parts -front end_________________________________________________________
def spare_parts_list(request):
    search_query = request.GET.get("search", "").strip()

    parts = SparePart.objects.filter(available=True)

    if search_query:
        parts = parts.filter(name__icontains=search_query)

    return render(request, "accounts/spare_parts_list.html", {
        "parts": parts,
        "search_query": search_query
    })

client = razorpay.Client(auth=(django_settings.RAZORPAY_KEY_ID, django_settings.RAZORPAY_KEY_SECRET))

@csrf_exempt
def create_razorpay_order(request, part_id):
    if request.method == "POST":
        data = json.loads(request.body)
        quantity = data.get("quantity", 1)

        part = SparePart.objects.get(id=part_id)
        amount = int(part.price * quantity * 100)  # in paise

        razorpay_order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": "1"
        })

        return JsonResponse({
            "order_id": razorpay_order['id'],
            "amount": razorpay_order['amount']
        })

@login_required
def book_part(request, part_id):
    part = SparePart.objects.get(id=part_id)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))

        # Check if enough stock is available
        if part.stock < quantity:
            messages.error(request, f"Only {part.stock} units available for {part.name}.")
            return redirect("spare_parts_list")

        total_amount = part.price * quantity
        payment_method = request.POST.get("payment_method")

        booking = BookedSparePart.objects.create(
            part=part,
            user=request.user,
            customer_name=request.POST.get("customer_name"),
            email=request.POST.get("email"),
            phone=request.POST.get("phone"),
            car_name=request.POST.get("car_name"),
            address=request.POST.get("address"),
            quantity=quantity,
            payment_method=payment_method,
            amount=total_amount
        )

        # Decrease stock after successful booking
        part.stock -= quantity
        part.save(update_fields=['stock'])

        if payment_method == 'online':
            booking.razorpay_order_id = request.POST.get('razorpay_order_id')
            booking.razorpay_payment_id = request.POST.get('razorpay_payment_id')
            booking.razorpay_signature = request.POST.get('razorpay_signature')
            booking.is_paid = True
            booking.save()
            messages.success(request, "Payment successful! Booking confirmed.")
        else:
            messages.success(request, "Booking confirmed! Please pay on delivery.")
            booking.save()

        # Send confirmation email
        send_mail(
            subject=f"Booking Confirmation for {part.name}",
            message=f"Hello {booking.customer_name},\n\nYour booking for {quantity} x {part.name} is confirmed.\nTotal Amount: ₹{total_amount}\nPayment Method: {payment_method}\n\nThank you!",
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.email],
            fail_silently=True,
        )

        return redirect("spare_parts_list")

    context = {
        "part": part,
        "RAZORPAY_KEY_ID": django_settings.RAZORPAY_KEY_ID
    }
    return render(request, "accounts/book_part.html", context)


# ________________refund_________________________________________________________
client = razorpay.Client(auth=(django_settings.RAZORPAY_KEY_ID, django_settings.RAZORPAY_KEY_SECRET))

def process_refund(payment_id, amount):
    """
    Refunds the given amount (in INR) for the payment_id.
    Returns True if refund succeeds, False otherwise.
    """

    try:
        client.payment.refund(payment_id, {'amount': int(amount*100)})
        return True
    except Exception as e:
        print("Refund failed:", e)
        return False
    
@admin_only
def refund_applications(request):

    messages_count = ContactMessage.objects.count()

    refund_bookings = Booking.objects.filter(
        Q(refund_requested=True) |
        Q(is_refunded=True)
    ).filter(
        is_removed=False
    ).exclude(booking_type='test_drive').order_by('-created_at')

    refund_spares = BookedSparePart.objects.filter(
        Q(refund_requested=True) |
        Q(is_refunded=True),
    ).filter(
        is_removed=False
    ).exclude(payment_method='cod').order_by('-created_at')

    context = {
        'refund_bookings': refund_bookings,
        'refund_spares': refund_spares,
        'messages_count': messages_count,
    }

    return render(request, "admin/refund_applications.html", context)


@login_required
def delete_booking_user(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if request.method == "POST":
        reason = request.POST.get("cancel_reason", "").strip()
        
        if booking.status not in ['Pending', 'Approved']:
            messages.error(request, "This booking cannot be cancelled.")
            return redirect('profile')

        booking.status = "Cancelled by User"
        booking.cancel_reason = reason
        booking.refund_requested = True  
        booking.save(update_fields=["status",  "refund_requested", "cancel_reason"])

        messages.success(request, "Booking cancelled successfully. Refund will be processed soon if applicable.")

    return redirect('profile')

@login_required
def spare_booking_delete(request, booking_id):
    booking = get_object_or_404(BookedSparePart, id=booking_id, user=request.user)

    if request.method == "POST":
        reason = request.POST.get("cancel_reason", "").strip()

  
        if booking.status in ['Cancelled by User', 'Cancelled by Admin'] or booking.is_refunded:
            messages.error(request, "This booking cannot be cancelled again.")
            return redirect('profile')

 
        if booking.status not in ['booked', 'delivered']:
            messages.error(request, "This booking cannot be cancelled.")
            return redirect('profile')

     
        booking.status = "Cancelled by User"
        booking.cancel_reason = reason
        booking.refund_requested = True  
        booking.save(update_fields=["deleted_by_user", "status", "cancel_reason", "refund_requested"])

        messages.success(request, "Spare part booking cancelled. Refund will be processed soon if applicable.")

    return redirect('profile')

@admin_only
def process_refund_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.is_refunded:
        messages.info(request, f"Booking #{booking.id} has already been refunded.")
        return redirect('refund_applications')

    if not booking.razorpay_payment_id:
        messages.error(request, "Cannot refund: No payment ID found.")
        return redirect('refund_applications')

    try:
        client.payment.refund(
            booking.razorpay_payment_id,
            {"amount": int(booking.advance_payment * 100)}
        )

        booking.is_refunded = True
        booking.refund_requested = False
        booking.status = "Refunded"
        booking.save(update_fields=["is_refunded", "refund_requested", "status"])

        send_mail(
            subject="Your Booking Refund Has Been Processed",
            message=(
                f"Dear {booking.name},\n\n"
                f"Your refund for Booking #{booking.id} has been successfully processed.\n"
                f"Amount: ₹{booking.advance_payment}\n\n"
                "Thank you for choosing us!"
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.email],
            fail_silently=False,
        )

        messages.success(request, f"Refund processed successfully for Booking #{booking.id} and email sent.")

    except Exception as e:
        messages.error(request, f"Refund failed for Booking #{booking.id}: {str(e)}")

    return redirect('refund_applications')

@admin_only
def process_refund_spare(request, spare_id):
    spare = get_object_or_404(BookedSparePart, id=spare_id)

    if spare.is_refunded:
        messages.info(request, f"Spare Part Booking #{spare.id} has already been refunded.")
        return redirect('refund_applications')

    if spare.payment_method != 'cod':
        if not spare.razorpay_payment_id:
            messages.error(request, "Cannot refund: No online payment ID found for this booking.")
            return redirect('refund_applications')

    try:
        client.payment.refund(
            spare.razorpay_payment_id,
            {"amount": int(spare.amount * 100)}
        )
        messages.success(request, f"Refund processed successfully for Spare Part Booking #{spare.id}.")
        spare.is_refunded = True
        spare.refund_requested = False
        spare.status = "Refunded"
        spare.save(update_fields=["is_refunded", "refund_requested", "status"])

   
        send_mail(
            subject="Your Spare Part Refund Has Been Processed",
            message=(
             f"Dear {spare.user.first_name},\n\n"
             f"Your refund for Spare Part Order #{spare.id} has been completed successfully.\n"
             f"Amount: ₹{spare.amount}\n\n"
             "We appreciate your patience.\n"
             "Thank you for choosing our service!"
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[spare.user.email],
            fail_silently=False,
        )



    except Exception as e:
        messages.error(request, f"Refund failed for Spare Part Booking #{spare.id}: {str(e)}")

    return redirect('refund_applications')

@admin_only
def delete_refund_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.is_removed = True
    booking.save(update_fields=["is_removed"])
    messages.success(request, "Booking moved to trash.")
    return redirect("refund_applications")

@admin_only
def delete_refund_spare(request, spare_id):
    spare = get_object_or_404(BookedSparePart, id=spare_id)
    spare.is_removed = True
    spare.save(update_fields=["is_removed"])
    messages.success(request, "Spare part refund entry moved to trash.")
    return redirect("refund_applications")

# ________________News Letter_________________________________________________________
@login_required
def subscribe_newsletter(request):
    if request.method == "POST":
        email = request.POST.get("email") or (request.user.email if request.user.is_authenticated else None)

        if not email:
            messages.error(request, "Please provide a valid email.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)

        # Attach user if logged in
        if request.user.is_authenticated:
            subscriber.user = request.user

        # --- FIXED LOGIC ---
        if created or not subscriber.is_subscribed:
            # New subscriber → subscribe
            subscriber.is_subscribed = True
            subscriber.save()
            messages.success(request, "You are now subscribed!")
        else:
            # Already subscribed → unsubscribe
            subscriber.is_subscribed = False
            subscriber.save()
            messages.info(request, "You have unsubscribed from the newsletter.")

        return redirect(request.META.get("HTTP_REFERER", "/"))

    return redirect("/")

@admin_or_staff_required
def newsletter_page(request):
    is_subscribed = False

    if request.user.is_authenticated:
        subscriber = NewsletterSubscriber.objects.filter(email=request.user.email, is_subscribed=True).first()
        if subscriber:
            is_subscribed = True

    return render(request, "your_template.html", {
        "is_subscribed": is_subscribed
    })


@admin_or_staff_required
def subscribers_list(request):
    messages_count = ContactMessage.objects.count()
    subscribers = NewsletterSubscriber.objects.filter(is_subscribed=True)
    context = {
        "subscribers": subscribers,
        "messages_count":messages_count
    }
    return render(request, "admin/subscribers.html", context)


@admin_or_staff_required
def send_offer(request):
    if request.method == "POST":
        subject = request.POST.get("subject")  
        message_text = request.POST.get("message")

        # Save the offer
        NewsletterMessage.objects.create(subject=subject, message=message_text)

        subscribers = NewsletterSubscriber.objects.filter(is_subscribed=True)
        emails = [(subject, message_text, None, [s.email]) for s in subscribers]

        send_mass_mail(emails, fail_silently=False)

        messages.success(request, "Offer sent successfully!")
        return redirect("subscribers_list")
    
@admin_only
def delete_subscriber(request, subscriber_id):
    if request.method == "POST":
        subscriber = get_object_or_404(NewsletterSubscriber, id=subscriber_id)
        subscriber.delete()
        messages.success(request, "Subscriber deleted successfully!")
    return redirect("subscribers_list")

def customer_autocomplete(request):
    q = request.GET.get("q", "")
    users = User.objects.filter(
        Q(username__icontains=q) |
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q)
    )[:10]

    results = [{"id": u.id, "name": u.get_full_name() or u.username} for u in users]

    return JsonResponse(results, safe=False)


# ________________excel and pdf_________________________________________________________
