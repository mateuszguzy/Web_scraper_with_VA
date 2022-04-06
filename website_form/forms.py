from django import forms
from django.forms import SelectDateWidget


class SearchForm(forms.Form):
    pages_to_search = forms.IntegerField(label='How many pages would you like to check:', min_value=0)
    date_in = forms.DateField(label='Check-in date:', widget=SelectDateWidget())
    date_out = forms.DateField(label='Checkout date:', widget=SelectDateWidget())
    adults = forms.IntegerField(label='Adults:', min_value=0)
    pets = forms.IntegerField(label='Pets:', min_value=0)
    house = forms.BooleanField(required=False)  # 1
    apartment = forms.BooleanField(required=False)  # 2
    cabin = forms.BooleanField(required=False)  # 4
    bungalow = forms.BooleanField(required=False)  # 38
    cottage = forms.BooleanField(required=False)  # 60
    bedrooms = forms.IntegerField(label='Bedrooms:', min_value=0)
    beds = forms.IntegerField(label='Beds:', min_value=0)
    bathrooms = forms.IntegerField(label='Bathrooms:', min_value=0)


class ChooseCurrency(forms.Form):
    choice = forms.ChoiceField(required=False, label=False, choices=(("USD", "USD"),
                                                                     ("EUR", "EUR"),
                                                                     ("GBP", "GBP"),
                                                                     ("DKK", "DKK"),
                                                                     ("PLN", "PLN"),
                                                                     ))


class FilterForm(forms.Form):
    choice = forms.ChoiceField(required=False, label=False, choices=(("", "None"),
                                                                     ("location", "Location"),
                                                                     ("max_guests", "Max Guests"),
                                                                     ("price", "Price"),
                                                                     ("title", "Title"),
                                                                     ))
