# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from .models import Car, CarImage
from .models import Profile
from .models import Booking

class CustomerSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')



# cars
class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = [
            'name', 'category', 'image', 'price', 'featured',
            'brand', 'model_year', 'engine_type', 'transmission',
            'fuel_type', 'mileage', 'seats', 'description'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class CarImageForm(forms.ModelForm):
    class Meta:
        model = CarImage
        fields = ['image']



class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

        
class AdminProfileImageForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['date', 'time', 'duration_days',"name", "email", "phone", "pickup_location", "notes"]

    def __init__(self, *args, **kwargs):
        booking_type = kwargs.pop('booking_type', None)
        super().__init__(*args, **kwargs)

        if booking_type == 'test_drive':
            self.fields['duration_days'].required = False
            self.fields['duration_days'].widget = forms.HiddenInput()
        elif booking_type == 'rent':
            self.fields['time'].required = False
            self.fields['time'].widget = forms.HiddenInput()
        else:
            self.fields['time'].required = False
            self.fields['duration_days'].required = False
            self.fields['time'].widget = forms.HiddenInput()
            self.fields['duration_days'].widget = forms.HiddenInput()


