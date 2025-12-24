# accounts/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import AdminPasswordChangeView 
from .views import removed_items

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),
    path('dashboard/user/', views.user_dashboard, name='home'),

    path('manage/<str:role>/', views.manage_users, name='manage_users'),
    path('manage/<str:role>/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('manage/<str:role>/delete/<int:user_id>/', views.delete_user, name='delete_user'),


    path('dashboard/admin/manage-cars/', views.manage_cars, name='manage_cars'),
    path('dashboard/admin/add-car/', views.add_car, name='add_car'),
    path('dashboard/admin/edit-car/<int:id>/', views.edit_car, name='edit_car'),
    path('dashboard/admin/delete-car/<int:car_id>/', views.delete_car, name='delete_car'),
    path('dashboard/admin/manage-cars/delete-selected/', views.delete_selected_cars, name='delete_selected_cars'),

    path('dashboard/admin/manage-bookings/', views.manage_bookings, name='manage_bookings'),
    path('dashboard/admin/approve-booking/<int:booking_id>/', views.approve_booking, name='approve_booking'),
    path('dashboard/admin/delete-booking/<int:booking_id>/', views.delete_booking_admin, name='delete_booking_admin'),
    path('dashboard/admin/remove-booking-row/<int:booking_id>/', views.remove_booking_row, name='remove_booking_row'),
    path('removed-bookings/delete/<int:booking_id>/', views.delete_removed_booking, name='delete_removed_booking'),
    path('removed-bookings/delete-all/', views.delete_all_removed_bookings, name='delete_all_removed_bookings'),
    path('complete-booking/<int:booking_id>/', views.complete_booking, name='complete_booking'),
    path('booking/<int:booking_id>/details/', views.booking_details, name='booking_details'),
    path('dashboard/admin/profile/', views.admin_profile, name='admin_profile'),
    path('dashboard/admin/add-booking/', views.add_booking, name='add_booking'),


    path('', views.home, name='home'), 
    path('cars/', views.car_list, name='car_list'), 
    path('cars/brand/<str:brand_name>/', views.car_brand_list, name='car_brand_list'),
 

    path('wishlist/toggle/<int:car_id>/',views.toggle_wishlist,name='toggle_wishlist'),
    path('car/<int:car_id>/', views.car_details, name='car_details'),

    path("customers/", views.manage_customers, name="manage_customers"),
    path('customers/delete/<int:customer_id>/',views.delete_customer,name='delete_customer'),
     path('dashboard/admin/add-customer-booking/', views.add_customer_with_booking, name='add_customer_booking'),

    path('dashboard/admin/manage_payments/', views.manage_payments, name='manage_payments'),
    path('dashboard/admin/delete_payment/<int:booking_id>/', views.delete_payment, name='delete_payment'),
    path('dashboard/admin/delete-multiple-payments/', views.delete_multiple_payments, name='delete_multiple_payments'),
    path('dashboard/admin/completed_payments/', views.completed_payments, name='completed_payments'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('pay-full/<int:booking_id>/', views.pay_full_amount, name='pay_full_amount'),
    path('payments/add/', views.add_payment, name='add_payment'),


    path("manage_services/", views.manage_services, name="manage_services"),
    path('manage_services/add/', views.add_service, name='add_service'),
    path('manage_services/<int:id>/edit/', views.edit_service, name='edit_service'),
    path('manage_services/<int:id>/delete/', views.delete_service, name='delete_service'),
    path('manage_services/<int:id>/view/', views.view_service, name='view_service'),
    path('verify_service_payment/', views.verify_service_payment, name='verify_service_payment'),

    path("reports/", views.reports, name="reports"),

    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path('autocomplete/', views.autocomplete_search, name='autocomplete_search'),
    path("profile/", views.profile, name="profile"),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<int:user_id>/', views.profile, name='profile-with-id'),
    path('submit-review/<int:booking_id>/', views.submit_review, name='submit_review'),
    path('submit-spare-review/<int:booking_id>/', views.submit_spare_review, name='submit_spare_review'),

    
    path('services/', views.services_list, name='services_list'), 
    path('services/<int:service_id>/', views.service_detail, name='service_detail'),
    path('category/<str:category_name>/', views.services_by_category, name='services_by_category'), 
    path('book_service/<int:service_id>/', views.book_service, name='book_service'),
    path('service/create-order/', views.create_service_order, name='create_service_order'),

    path('customer/<int:user_id>/', views.customer_profile, name='customer_profile'),
    path('customer/<int:id>/bookings/', views.customer_bookings, name='customer_bookings'),

    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),

    path('book/<int:car_id>/<str:booking_type>/', views.book_car_action, name='book_car_action'),
    

    path('dashboard/admin/removed-items/', removed_items, name='removed_items'),
    path('dashboard/admin/removed-items/action/', views.bulk_removed_action, name='bulk_removed_action'),

    path('dashboard/admin/contact-messages/', views.admin_contact_messages, name='admin_contact_messages'),
    path('notifications/delete/<int:pk>/', views.delete_message, name='delete_message'),
    path('dashboard/admin/review/accept/<int:review_id>/', views.accept_review, name='accept_review'),
    path('dashboard/admin/review/reject/<int:review_id>/', views.reject_review, name='reject_review'),
    path('dashboard/admin/review/delete/<int:review_id>/', views.delete_review, name='delete_review'),

    path('send-all-due-emails/', views.send_all_due_emails, name='send_all_due_emails'),

    path('dashboard/change-password/', AdminPasswordChangeView.as_view(), name='admin_change_password'),

    path('dashboard/spare-parts/', views.manage_spare_parts, name='manage_spare_parts'),
    path('dashboard/spare-parts/edit/<int:part_id>/', views.edit_spare_part, name='edit_spare_part'),
    path('dashboard/spare-parts/delete/<int:part_id>/', views.delete_spare_part, name='delete_spare_part'),
    path('dashboard/spare-parts/bulk-delete/', views.bulk_delete_spare_parts, name='bulk_delete_spare_parts'),
    path('booked-spare-parts/', views.booked_spare_parts, name='booked_spare_parts'),
    path('booked-spare-parts/<int:booking_id>/deliver/', views.mark_delivered, name='mark_delivered'),
    path('booked-spare-parts/<int:booking_id>/delete/', views.delete_booking, name='delete_booking'),


    path('spare-parts/', views.spare_parts_list, name='spare_parts_list'),

    path('book/<int:part_id>/', views.book_part, name='book_part'),
    path('create-razorpay-order/<int:part_id>/', views.create_razorpay_order, name='create_razorpay_order'),

    path('cancel-booking/<int:booking_id>/', views.delete_booking_user, name='delete_booking_user'),
    path('cancel-spare-booking/<int:booking_id>/', views.spare_booking_delete, name='spare_booking_delete'),

    path('refund-applications/', views.refund_applications, name='refund_applications'),

    path("refund-booking/<int:booking_id>/", views.process_refund_booking, name="process_refund_booking"),
    path("refund-spare/<int:spare_id>/", views.process_refund_spare, name="process_refund_spare"),

    path("refund/delete-booking/<int:booking_id>/", views.delete_refund_booking, name="delete_refund_booking"),
    path("refund/delete-spare/<int:spare_id>/", views.delete_refund_spare, name="delete_refund_spare"),

    path("subscribe/", views.subscribe_newsletter, name="subscribe_newsletter"),

    # urls.py
    path("dashboard/admin/subscribers/", views.subscribers_list, name="subscribers_list"),
    path("dashboard/admin/send-offer/", views.send_offer, name="send_offer"),
    path("dashboard/admin/subscribers/delete/<int:subscriber_id>/", views.delete_subscriber, name="delete_subscriber"),

    path("customer-autocomplete/", views.customer_autocomplete, name="customer_autocomplete"),
    path('booking/remove/<int:booking_id>/', views.remove_booking_user, name='remove_booking_user'),
    path('spare-booking/remove/<int:booking_id>/', views.remove_spare_booking_user, name='remove_spare_booking_user'),
    

    

]
