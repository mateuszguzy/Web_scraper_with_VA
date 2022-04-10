from django.shortcuts import render, reverse
from django.http import HttpResponseRedirect
from django.utils.datastructures import MultiValueDictKeyError
from django.core.exceptions import ObjectDoesNotExist, FieldError
from .models import Offers
from .forms import SearchForm, ChooseCurrency, FilterForm
from dotenv import load_dotenv
import bs4
import requests
import speech_recognition as sr
import time
import re
import os
from playsound import playsound


load_dotenv()
# Initializing the speech recognizer and text to speech converter API
listener = sr.Recognizer()

# ------ DEFINE CONSTANTS
API_KEY = os.environ.get("CURRENCY_EXCHANGE_API")
SYNTH_API_KEY = os.environ.get("SYNTH_API_KEY")
CURRENCY = "USD"
DATA = Offers.objects.all()
CURRENCY_EXCHANGE_URL = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{CURRENCY}"
SYNTH_API_URL = f"http://api.voicerss.org/?key={SYNTH_API_KEY}&hl=en-us&v=Amy&src="
AUDIO_DIR = 'website_form/static/website_form/'


def index(request):
    """Function takes input from online form and scrapes Air BnB site with parameters defined in form."""
    # TODO - Note
    # form must have "request.POST or None" as attributes or will not validate form
    form = SearchForm(request.POST or None)
    if request.method == "POST" and "search" in request.POST:
        # --- USE DATA FROM FORM
        # assign data from form to filters passed later into URL
        pages_to_search = int(form.data["pages_to_search"])
        # format date extracted from online form in correct form
        date_in = f"{form.data['date_in_year']}-{form.data['date_in_month']}-{form.data['date_in_day']}"
        date_out = f"{form.data['date_out_year']}-{form.data['date_out_month']}-{form.data['date_out_day']}"
        real_estate_types = str()
        real_estate_types_list = list()
        # "multiple choices checkboxes"
        # form checkboxes return "on" when checked, so to determine which estate type user want to search
        # a "middle-agent" dictionary was created
        real_estate_types_dict = {
            "1": "house",
            "2": "apartment",
            "4": "cabin",
            "38": "bungalow",
            "60": "cottage"
        }
        for estate_type in real_estate_types_dict.values():
            # while checkbox is unchecked there is no "False" so error occurs, that's why "try/except"
            try:
                # check if form has any of the values from dictionary above
                if form.data[estate_type]:
                    # if yes find keys by reverse search in key/values lists
                    position = list(real_estate_types_dict.values()).index(estate_type)
                    real_estate_types_list.append(list(real_estate_types_dict.keys())[position])
            except MultiValueDictKeyError:
                # in case of error omit that value
                pass
        for estate_type in real_estate_types_list:
            # depending on how many estate types user selected add that many lines with "property type" attribute
            real_estate_types += f"&property_type_id%5B%5D={estate_type}"
        pets = form.data["pets"]
        adults = form.data["adults"]
        min_bedrooms = form.data["bedrooms"]
        min_beds = form.data["beds"]
        min_bathrooms = form.data["bathrooms"]
        # combine data from form into URL
        flat_renting_url = f"https://www.airbnb.com/s/Denmark/" \
                           f"homes?tab_id=home_tab" \
                           f"&refinement_paths%5B%5D=%2Fhomes" \
                           f"&flexible_trip_dates[]=april&flexible_trip_dates[]=march" \
                           f"&flexible_trip_lengths[]=weekend_trip" \
                           f"&date_picker_type=calendar" \
                           f"&checkin={date_in}" \
                           f"&checkout={date_out}" \
                           f"&query=Denmark&place_id=ChIJ-1-U7rYnS0YRzZLgw9BDh1I" \
                           f"&source=structured_search_input_header" \
                           f"&room_types%5B%5D=Entire%20home%2Fapt" \
                           f"&pets={pets}" \
                           f"&adults={adults}" \
                           f"{real_estate_types}" \
                           f"&min_bedrooms={min_bedrooms}" \
                           f"&min_beds={min_beds}" \
                           f"&min_bathrooms={min_bathrooms}" \
                           f"&pagination_search=true"
        page_scraper(flat_renting_url=flat_renting_url, pages_to_search=pages_to_search)
        return HttpResponseRedirect(reverse("website_form:results"))

    if request.method == "POST" and "voice_assistant" in request.POST:
        voice_assistant()
        return HttpResponseRedirect(reverse("website_form:results"))
    return render(request, "website_form/form.html", {"form": form})


def page_scraper(flat_renting_url, pages_to_search):
    titles = list()
    locations = list()
    dates = list()
    prices = list()
    images = list()
    links = list()
    max_guests_list = list()

    for page in range(pages_to_search):
        # parameter responsible for jumping to another result page
        # Air BnB allows only 20 results, starting from zero
        item_offset = page * 20
        flat_renting_url += f"&items_offset={item_offset}&section_offset=6"
        # get filtered response from website and prepare soup
        # print(flat_renting_url)
        web_page_response = requests.get(url=flat_renting_url)
        soup = bs4.BeautifulSoup(web_page_response.text, "html.parser")
        # separate content with only searched flats listed
        all_flats = soup.find_all(name="div", class_="_fhph4u")
        links_to_offers = list()
        print(f"Scraping page: {page + 1}")
        for flat in all_flats:
            # extract all links from h1 tags
            step_one_to_link = flat.find_all(name="meta", itemprop="url")
            # step_one_to_price = flat.find_all(name="span", class_="a8jt5op dir dir-ltr")
            step_one_to_price = flat.find_all("div", {"class": "_1jo4hgw"})
            # print(step_one_to_price)
            # finally, extract only URL
            for link in step_one_to_link:
                links_to_offers.append(link.get("content"))
            # extract price value
            for price in step_one_to_price:
                if len(price.text) < 17:
                    prices.append(price.text.split(" ")[0][1:-1].strip())
                else:
                    prices.append(price.text.split(" ")[0][:-1].strip().split("$")[-1])
        counter = 1
        # scrape every link that was extracted from main page to gain more detailed data
        for link in links_to_offers:
            print(f"{counter}. Extracting data...")
            links.append(f"https://{link}")
            single_result = requests.get(url=f"https://{link}")
            soup = bs4.BeautifulSoup(single_result.text, "html.parser")
            # title
            title = soup.find(name="h1", class_="_fecoyn4")
            titles.append(title.text)
            # location
            location = soup.find(name="span", class_="_8vvkqm3")
            locations.append(location.text)
            # in-out dates
            date = soup.find(name="div", class_="_uxnsba")
            dates.append(date.text)
            # main image
            image = soup.find(name="img", class_="_6tbg2q")
            images.append(image.get("src"))
            # max guests
            max_guests = soup.find(name="ol", class_="l7n4lsf dir dir-ltr")
            max_guests_list.append(max_guests.text.split("·")[0].strip())
            counter += 1
            # wait 1sec, for faster scrape Air BnB security triggers
            time.sleep(1)
    scraped_data_processing(titles, locations, dates, prices, images, links, max_guests_list)


def scraped_data_processing(titles, locations, dates, prices, images, links, max_guests_list):
    all_data = {"title": list(), "location": list(), "date_in": list(), "date_out": list(), "max_guests": list(),
                "price": list(), "link": list(), "image": list()}
    months = {
        "Jan": "01",
        "Feb": "02",
        "Mar": "03",
        "Apr": "04",
        "May": "05",
        "Jun": "06",
        "Jul": "07",
        "Aug": "08",
        "Sep": "09",
        "Oct": "10",
        "Nov": "11",
        "Dec": "12",
    }
    for i in range(len(titles)):
        date_in_extract = dates[i].split("-")[0].strip().split(" ")
        date_out_extract = dates[i].split("-")[1].strip().split(" ")
        # change extracted month description in string to int, so it can be saved in DB
        date_in = f"{date_in_extract[2]}-{months[date_in_extract[0]]}-{date_in_extract[1][:-1]}"
        date_out = f"{date_out_extract[2]}-{months[date_out_extract[0]]}-{date_out_extract[1][:-1]}"
        if len(prices[i]) > 3:
            price = prices[i].replace(",", "")
        else:
            price = prices[i]
        # on few pages some results are repeating
        # check if given title is present in "all_data" dictionary, if yes omit that data
        # if no, add all data into "all_data" dictionary
        if titles[i] in all_data["title"]:
            pass
        else:
            # on another scraping (new form), check if any result is repeating if yes - omit
            try:
                Offers.objects.get(title=titles[i])
            except ObjectDoesNotExist:
                Offers.objects.create(
                    title=titles[i],
                    location=locations[i],
                    date_in=date_in,
                    date_out=date_out,
                    max_guests=max_guests_list[i][0],
                    price=price,
                    link=links[i],
                    picture=images[i],
                    converted_price=0,
                )
    return HttpResponseRedirect(reverse("website_form:results"))


def results(request):
    """Show all results stored in DB. Allows using filters on data, and currency exchange based on latest rates. """
    # global variables used to keep filters on while currency is changed and in reverse
    global CURRENCY, DATA
    currency_change_form = ChooseCurrency(request.POST or None)
    filter_form = FilterForm(request.POST or None)

    # when price is updated, user "reverse" to load whole view one more time
    # to update view with whole DB. If not, currency exchange will not take into account newly added price
    if request.method == "POST" and "price" in request.POST:
        offer_to_update = Offers.objects.get(id=request.POST["offer_id"])
        offer_to_update.price = request.POST["price"]
        offer_to_update.save()
        return HttpResponseRedirect(reverse("website_form:results"))
    # base currency is USD if any other is chosen run exchange_currency()
    if request.method == "POST" and "change_currency" in request.POST:
        currency_type = currency_change_form.data
        if currency_type["choice"] != CURRENCY:
            exchange_currency(currency_type["choice"])
            # change global var CURRENCY so that after using filters chosen currency will still be shown
            CURRENCY = currency_type["choice"]
    elif request.method == "POST" and "apply_filters" in request.POST:
        # try/except because when filter "None" is selected DB error occurs.
        # In that case that means that there's no need for "order_by" and get from DB all data in default order
        try:
            if filter_form.data["choice"] == "location" or filter_form.data["choice"] == "title":
                DATA = Offers.objects.order_by(filter_form.data["choice"])
            else:
                DATA = Offers.objects.order_by(filter_form.data["choice"]).reverse()
        except FieldError:
            DATA = Offers.objects.all()
    # if no filters/currency exchange is made just take default values from DB
    else:
        DATA = Offers.objects.all()
    return render(request, "website_form/results.html", {"data": DATA, "currency_change_form": currency_change_form,
                                                         "currency": CURRENCY, "filter_form": filter_form})


def exchange_currency(currency_type):
    """Fetch current exchange rates from 'Exchange Rate', based on given currency type."""
    # because from Air BnB scraped price is in USD, to swiftly convert to other currencies
    # another column was made so that original price is always saved in DB
    # but other currencies are flexible given current exchange rate
    exchange_value = requests.get(CURRENCY_EXCHANGE_URL).json()
    for offer in DATA:
        offer.converted_price = int(offer.price * float(exchange_value["conversion_rates"][currency_type]))
        offer.save()


def voice_assistant():
    """Allows to remotely fill the form present on website. Ask questions covering all the fields
    present in online form, and starts data scraping function."""
    # hard coded dictionary represents all the form fields questions
    form_fields = {
        "1": {
            "question": "How many pages would you like to check?",
            "input_type": "int",
            "sentence": "You want to check %s page%s"
        },
        "2": {
            "question": "When do you want to check-in?",
            "input_type": "date",
            "sentence": "You want to check-in %s%s of %s, %s",
        },
        "3": {
            "question": "When do you want to checkout?",
            "input_type": "date",
            "sentence": "You want to checkout %s%s of %s, %s",
        },
        "4": {
            "question": "How many adults are coming?",
            "input_type": "int",
            "sentence": "You want to bring %s adult%s.",
        },
        "5": {
            "question": "How many pets are you taking?",
            "input_type": "int",
            "sentence": "You want to bring %s pet%s.",
        },
        "6": {
            "question": "Please tell me, which from below stated property types are you willing to stay in? House, "
                        "apartment, cabin, bungalow, cottage.",
            "input_type": "property",
            "sentence": "You are willing to stay in %s.",
        },
        "7": {
            "question": "How many bedrooms should searched property have?",
            "input_type": "int",
            "sentence": "You want to have %s bedroom%s.",
        },
        "8": {
            "question": "How many beds should searched property have?",
            "input_type": "int",
            "sentence": "You want to have %s bed%s.",
        },
        "9": {
            "question": "How many bathroom should searched property have?",
            "input_type": "int",
            "sentence": "You want to have %s bathroom%s.",
        },
    }
    # for modifying scraped data, so it can be saved in DB
    months = {
                "january": "01",
                "february": "02",
                "march": "03",
                "april": "04",
                "may": "05",
                "june": "06",
                "july": "07",
                "august": "08",
                "september": "09",
                "october": "10",
                "november": "11",
                "december": "12",
            }
    # base values of variables that later will be passed into correct URL
    number_of_pages = str()
    date_in = str()
    date_out = str()
    adults = str()
    pets = str()
    real_estate_types = str()
    min_bedrooms = str()
    min_beds = str()
    min_bathrooms = str()

    # ------ Initialize VA
    playsound(f'{AUDIO_DIR}hello.wav')
    time.sleep(1)
    # --- Iterate through every field in dictionary
    for i in form_fields:
        # ask field question only once
        question_audio_from_url = requests.get(SYNTH_API_URL + (form_fields[i]["question"]))
        with open(f"{AUDIO_DIR}{i}q.wav", "wb") as file:
            file.write(question_audio_from_url.content)
        playsound(f'{AUDIO_DIR}{i}q.wav')
        # when voice command could not be interpreted stay in loop until input will be correct
        move_on = False
        while move_on is False:
            command = speech_recognition()
            # variables returned from func assigned as tuple
            # for each "input_type" number of variables will differ, but "move_on" is always last
            variables = command_interpreter(command=command, input_type=form_fields[i]["input_type"])
            # when something is wrong with voice input, "command_interpreter" function will return "move_on"
            # variable as "False"
            move_on = variables[-1]
        # after correct input read user input
        confirmation_audio_from_url = requests.get(SYNTH_API_URL + (form_fields[i]["sentence"] % variables[:-1]))
        with open(f"{AUDIO_DIR}{i}a.wav", "wb") as file:
            file.write(confirmation_audio_from_url.content)
        playsound(f'{AUDIO_DIR}{i}a.wav')
        # hard coded for every question
        # assign variables needed to create correct URL
        if i == "1":
            number_of_pages = variables[0]
        elif i == "2":
            # for single digit integers add zero, so it can be passed in correct form to URL
            if len(variables[0]) == 1:
                day_in = "0" + variables[0]
            else:
                day_in = variables[0]
            month_in = variables[2]
            year_in = variables[3]
            date_in = f"{year_in}-{months[month_in]}-{day_in}"
        elif i == "3":
            # for single digit integers add zero, so it can be passed in correct form to URL
            if len(variables[0]) == 1:
                day_out = "0" + variables[0]
            else:
                day_out = variables[0]
            month_out = variables[2]
            year_out = variables[3]
            date_out = f"{year_out}-{months[month_out]}-{day_out}"
        elif i == "4":
            adults = variables[0]
        elif i == "5":
            pets = variables[0]
        elif i == "6":
            real_estate_types = variables[0]
        elif i == "7":
            min_bedrooms = variables[0]
        elif i == "8":
            min_beds = variables[0]
        elif i == "9":
            min_bathrooms = variables[0]
    flat_renting_url = f"https://www.airbnb.com/s/Denmark/" \
                       f"homes?tab_id=home_tab" \
                       f"&refinement_paths%5B%5D=%2Fhomes" \
                       f"&flexible_trip_dates[]=april&flexible_trip_dates[]=march" \
                       f"&flexible_trip_lengths[]=weekend_trip" \
                       f"&date_picker_type=calendar" \
                       f"&checkin={date_in}" \
                       f"&checkout={date_out}" \
                       f"&query=Denmark&place_id=ChIJ-1-U7rYnS0YRzZLgw9BDh1I" \
                       f"&source=structured_search_input_header" \
                       f"&room_types%5B%5D=Entire%20home%2Fapt" \
                       f"&pets={pets}" \
                       f"&adults={adults}" \
                       f"{real_estate_types}" \
                       f"&min_bedrooms={min_bedrooms}" \
                       f"&min_beds={min_beds}" \
                       f"&min_bathrooms={min_bathrooms}" \
                       f"&pagination_search=true"
    playsound(f"{AUDIO_DIR}search_start.wav")
    page_scraper(flat_renting_url, int(number_of_pages))


def command_interpreter(command, input_type):
    """Validates interpreted voice input from user. It's divided in three types: integers, date and property type.
    Type depend on field that currently VA is trying to validate."""
    # dictionary for checking numbers interpreted as words
    numerals_in_words = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6"}
    months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
              "november", "december"]
    # when integer is needed for form field, look for one or two digits in command
    if input_type == "int":
        regex = '\d{1,2}'
        output = re.search(regex, command)
        # if digits are not found it may mean that interpreter returned numeral in word form
        # try to check if that's true for a couple of numbers, if not get back to listening loop
        if output is None:
            try:
                for key in numerals_in_words.keys():
                    if key in command:
                        number = numerals_in_words[key]
            except KeyError:
                playsound(f"{AUDIO_DIR}error.wav")
                return None, None, False
        else:
            number = output.group()
        # assign correct suffix for engine to use
        try:
            if int(number) > 1:
                plural = "s"
            else:
                plural = ""
        except UnboundLocalError:
            playsound(f"{AUDIO_DIR}error.wav")
            return None, None, False
        return number, plural, True
    # when "input_type" is a date firstly look for one or two digits (days), and next for four
    # consecutive digits (year)
    elif input_type == "date":
        regex_day = '\d{1,2}'
        regex_year = '\d{4}'
        day = re.search(regex_day, command)
        year = re.search(regex_year, command)
        # if regex match assign correct suffixes
        if day is not None and year is not None:
            if int(day.group()[-1]) == 1:
                suffix = "st"
            elif int(day.group()[-1]) == 2:
                suffix = "nd"
            elif int(day.group()[-1]) == 3:
                suffix = "rd"
            else:
                suffix = "th"
        else:
            playsound(f"{AUDIO_DIR}error.wav")
            return None, None, None, None, False
        # check if month was interpreted correctly
        month = None
        for m in months:
            if m in command:
                month = m
                return day.group(), suffix, month, year.group(), True
        if month is None:
            playsound(f"{AUDIO_DIR}error.wav")
            return None, None, None, None, False

    elif input_type == "property":
        property_types = ["house", "apartment", "cabin", "bungalow", "cottage"]
        chosen_property_types = [property_type for property_type in property_types if property_type in command]
        if not chosen_property_types:
            playsound(f"{AUDIO_DIR}error.wav")
            return None, False
        return chosen_property_types, True


def speech_recognition():
    run = True
    # when mic gets no input, stays in a loop until some voice input is provided
    # when some voice is yet recognized, it's passed further to "command_interpreter()" for further validation
    while run:
        with sr.Microphone() as mic:
            print("Listening")
            listener.adjust_for_ambient_noise(mic)
            voice = listener.listen(mic, timeout=15)
        try:
            print("Recognizing...")
            voice_command = listener.recognize_google(voice)
            print(f"You said: {voice_command}")
            return voice_command.lower()
        except sr.UnknownValueError:
            print("Not recognized")
            playsound(f"{AUDIO_DIR}error.wav")
