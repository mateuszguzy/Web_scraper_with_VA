from django.db import models


# Create your models here.
class Offers(models.Model):
    objects = None
    title = models.CharField('Title', max_length=200)
    location = models.CharField('Location', max_length=50)
    date_in = models.DateField('Date In')
    date_out = models.DateField('Date Out')
    max_guests = models.IntegerField('Max Guests')
    price = models.IntegerField('Price')
    # because from Air BnB scraped price is in USD, to swiftly convert to other currencies
    # another column was made so that original price is always saved in DB
    # but other currencies are flexible given current exchange rate
    converted_price = models.IntegerField('Converted Price')
    link = models.URLField('Offer Link')
    picture = models.URLField('Image Link')
