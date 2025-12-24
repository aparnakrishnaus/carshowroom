from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Booking


class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )


admin.site.register(User, CustomUserAdmin)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'car', 'booking_type', 'date', 'time', 'status', 'created_at')
    list_filter = ('booking_type', 'status', 'date')
    search_fields = ('user__username', 'car__name')
    ordering = ('-created_at',)
