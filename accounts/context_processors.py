from .models import Car, Service, User
from collections import defaultdict
from .models import Booking ,ContactMessage, Review,BookedSparePart,  NewsletterSubscriber
from django.db.models import Q
from django.conf import settings


def brands_processor(request):
    brands = Car.objects.values_list('brand', flat=True).distinct()
    
    services = Service.objects.all().order_by('name')
    grouped_services = defaultdict(list)
    for service in services:
        grouped_services[service.category or 'Uncategorized'].append(service)

    categories = Service.objects.values_list('category', flat=True).distinct()
    categories = [cat or 'Uncategorized' for cat in categories]

    return {
        'brands': brands,
        'grouped_services': dict(grouped_services),
        'categories': categories
    }


def admin_sidebar_counts(request):
    if not request.user.is_authenticated:
        return {}

    new_booking_count = Booking.objects.filter(
        status__iexact="Pending",
        is_removed=False
    ).count()

    try:
        new_payment_count = Booking.objects.filter(
            is_fully_paid=False,
            is_advance_paid=True
        ).count()
    except:
        new_payment_count = 0  

    counts = {
        "bookings": Booking.objects.filter(is_removed=True).count(),
        "booked_parts": BookedSparePart.objects.filter(is_removed=True).count(),
        "customers": User.objects.filter(role='customer', is_removed=True).count(),
        "staff": User.objects.filter(is_staff=True, is_superuser=False, is_removed=True).count(),
        "admin": User.objects.filter(is_superuser=True, is_removed=True).count(),
        "payments": Booking.objects.filter(
            Q(advance_payment__gt=0) | Q(balance__gt=0),
            is_removed=True
        ).count(),
    }


    total_trash = sum(counts.values())

    unread_notifications_count = ContactMessage.objects.count() + Review.objects.count()

    subscribers_count = NewsletterSubscriber.objects.filter(is_subscribed=True).count()

    booked_spare_parts_count = BookedSparePart.objects.filter(status='booked', is_removed=False).count()

    
    refund_booking_count = Booking.objects.filter(refund_requested=True,is_refunded=False,is_removed=False,).count()
    refund_spare_count = BookedSparePart.objects.filter(refund_requested=True,is_refunded=False,is_removed=False,payment_method__iexact="online").count()
    refund_count = refund_booking_count + refund_spare_count


    return {
        "new_booking_count": new_booking_count,
        "new_payment_count": new_payment_count,
        "total_trash": total_trash, 
        "unread_notifications_count": unread_notifications_count,
        "booked_spare_parts_count": booked_spare_parts_count,
        "refund_count": refund_count,  
        "subscribers_count": subscribers_count,
    }


def subscription_status(request):
    """
    Returns whether the logged-in user is subscribed.
    Available in all templates.
    """
    is_subscribed = False
    if request.user.is_authenticated:
        subscriber = NewsletterSubscriber.objects.filter(
            email=request.user.email,
            is_subscribed=True
        ).first()
        if subscriber:
            is_subscribed = True

    return {"is_subscribed": is_subscribed}



def social_links(request):
    return {
        "social_links": getattr(settings, "SOCIAL_LINKS", {})
    }
