import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from hypothesis import Verbosity, given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver

from page_objects.registration_page import RegistrationFormPage
from utilities.ublock import download_and_extract_latest_ublock

hypothesis_settings.register_profile(
    "debug", max_examples=100, deadline=None, verbosity=Verbosity.verbose
)
hypothesis_settings.load_profile("debug")


PICTURES_DIR = Path(__file__).parent / "pictures"


def get_driver(time_to_wait: float = 1.0) -> WebDriver:
    chrome_options = Options()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.add_argument("force-device-scale-factor=0.75")
    # chrome_options.add_argument("high-dpi-support=0.75")
    extension_path = download_and_extract_latest_ublock()
    chrome_options.add_argument(f"--load-extension={extension_path}")
    drv = webdriver.Chrome(options=chrome_options)
    drv.implicitly_wait(time_to_wait)
    drv.maximize_window()
    return drv


@pytest.fixture(scope="session")
def driver(time_to_wait: float = 1):
    drv = get_driver(time_to_wait)
    yield drv
    drv.quit()


def get_registration_page(drv: WebDriver) -> RegistrationFormPage:
    drv.get("https://demoqa.com/automation-practice-form")
    return RegistrationFormPage(drv)


@pytest.fixture(scope="session")
def registration_page(driver: WebDriver) -> RegistrationFormPage:
    return get_registration_page(driver)


def possible_values(
    use_cache: bool = True,
    cache_path=Path(__file__).parent / "possible_values.json",
) -> dict[str, Any]:
    if use_cache and cache_path.exists():
        with open(cache_path, "rt", encoding="utf-8") as fp:
            possible_values = json.load(fp)
    else:
        drv = get_driver(2.0)
        page = get_registration_page(drv)
        possible_values = {
            "genders": page.scrape_genders(),
            "hobbies": page.scrape_hobbies(),
            "subjects": page.scrape_subjects(),
            "state_city_map": page.scrape_states_and_cities(),
        }
        page.reset()
        drv.quit()
        with open(cache_path, "wt", encoding="utf-8") as fp:
            json.dump(possible_values, fp, indent=4, ensure_ascii=False)

    return possible_values


@dataclass
class FieldStrategies:
    valid: st.SearchStrategy
    invalid: st.SearchStrategy


def hypothesis_strategies(
    possible_values: dict[str, Any],
) -> dict[str, FieldStrategies]:
    # Space, the first printable character in the ASCII character set
    min_supported = 0x20
    # End of the Basic Multilingual Plane
    max_supported = 0xFFFF
    latin_alpha = "abcdefghijklmnopqrstuvwxyz"
    digits = "1234567890"

    # Names and addresses with at least one alphabetical character are valid
    # My choice on allowing names to contain digits is based on:
    # https://github.com/kdeldycke/awesome-falsehood
    valid_name_or_address: SearchStrategy[str] = (
        st.text(
            alphabet=st.characters(
                min_codepoint=min_supported,
                max_codepoint=max_supported,
                categories=(
                    "Ll",  # Lowercase letters
                    "Lu",  # Uppercase letters
                    "Nd",  # Digits
                ),
                include_characters="-' ",
            ),
            min_size=1,
            max_size=300,
        )
        .filter(lambda s: any(c.isalpha() for c in s))
        .map(str.strip)
    )  # Assume a valid name/address has at least 1 letter

    invalid_name_or_address: SearchStrategy[str | None] = st.one_of(
        st.none(),
        # String without letters
        st.text(
            alphabet=st.characters(
                min_codepoint=min_supported,
                max_codepoint=max_supported,
                categories=("S", "P", "N"),
                include_characters="-' ",
            ),
            min_size=1,
        ).map(str.strip),
        # Extremely long string
        st.text(
            min_size=300,
            alphabet=st.characters(
                min_codepoint=min_supported,
                max_codepoint=max_supported,
                exclude_categories=("C",),
            ),
        ).map(str.strip),
    )

    valid_email = st.emails()

    valid_email_alphabet = latin_alpha + digits + "-_."

    invalid_email: SearchStrategy[str | None] = st.one_of(
        st.none(),
        # Missing '@' symbol
        st.text(
            alphabet=st.characters(
                min_codepoint=min_supported,
                max_codepoint=max_supported,
                exclude_characters="@",
                exclude_categories=("C",),
            )
            .map(lambda x: x + ".com")
            .map(str.strip)
        ),
        # Starting with special characters with no escape
        st.text(alphabet="!#$%^&*()", min_size=1, max_size=10).map(
            lambda x: x + "@example.com"
        ),
        # Missing domain part
        st.text(
            min_size=1,
            alphabet=st.characters(
                min_codepoint=min_supported,
                max_codepoint=max_supported,
                exclude_categories=("C",),
            ),
        )
        .map(lambda x: x + "@")
        .map(str.strip),
        # Valid structure but with repeated nonsensical domain parts
        st.text(alphabet=valid_email_alphabet, min_size=1, max_size=10).map(
            lambda local: f"{local}@----....com"
        ),
        # RFC 3696, Errata ID 1690
        st.text(
            min_size=255,
            max_size=300,
            alphabet=valid_email_alphabet,
        ).map(lambda x: x + "@example.com"),
        # Valid structure but with invalid domain parts
        st.text(alphabet=valid_email_alphabet).map(lambda x: x + "@!#$.com"),
    )

    @st.composite
    def valid_state_and_city(
        draw, state_strategy=st.sampled_from(list(possible_values["state_city_map"]))
    ):
        state = draw(state_strategy)
        cities = possible_values["state_city_map"][state]
        city = draw(st.sampled_from(cities))
        return state, city

    # Assuming that choosing state while not choosing city is invalid
    @st.composite
    def invalid_state_and_city(
        draw,
        state_strategy=st.one_of(
            st.sampled_from(list(possible_values["state_city_map"])), st.none()
        ),
    ):
        state = draw(state_strategy)
        city = draw(st.none())
        return state, city

    valid_gender = st.sampled_from(possible_values["genders"])
    invalid_gender = st.none()
    invalid_picture = st.one_of(
        st.none(), st.just(str(PICTURES_DIR / "invalid_picture.txt"))
    )

    @st.composite
    def valid_gender_and_picture(draw):
        gender_strategy = valid_gender
        gender = draw(gender_strategy)
        picture_strategy = st.sampled_from(list((PICTURES_DIR / gender).glob("*.jpeg")))
        picture = str(draw(picture_strategy))
        return gender, picture

    # Assuming students can be 16-60 years old
    # Taking into account leap years by averaging a year as 365.25 days
    valid_date_of_birth = st.dates(
        min_value=(datetime.now() - timedelta(days=365.25 * 60)).date(),
        max_value=(datetime.now() - timedelta(days=365.25 * 16)).date(),
    )

    # Students can't be newborns or be born in the future.
    invalid_date_of_birth = st.dates(min_value=datetime.today().date())

    # Assuming 3+ leading zeros are possible
    # https://en.wikipedia.org/wiki/List_of_international_call_prefixes
    valid_mobile = st.text(alphabet=digits, min_size=10, max_size=10)

    invalid_mobile = st.one_of(
        # Numbers with fewer than 10 digits
        st.text(alphabet=digits, min_size=1, max_size=9),
        # Strings with non-numeric characters
        st.text(
            alphabet=st.characters(
                min_codepoint=min_supported,
                max_codepoint=max_supported,
                exclude_categories=("Nd", "C"),
            ),
            min_size=1,
            max_size=10,
        ),
        st.none(),
    )

    valid_hobbies = st.lists(st.sampled_from(possible_values["hobbies"]), unique=True)

    valid_subjects = st.lists(
        st.sampled_from(possible_values["subjects"]), unique=True, min_size=1
    )
    invalid_subjects = st.none()

    return {
        "first_name": FieldStrategies(valid_name_or_address, invalid_name_or_address),
        "last_name": FieldStrategies(valid_name_or_address, invalid_name_or_address),
        "gender_and_picture": FieldStrategies(valid_gender_and_picture(), None),
        "gender": FieldStrategies(None, invalid_gender),
        "picture": FieldStrategies(None, invalid_picture),
        "email": FieldStrategies(valid_email, invalid_email),
        "subjects": FieldStrategies(valid_subjects, invalid_subjects),
        "hobbies": FieldStrategies(valid_hobbies, None),
        "date_of_birth": FieldStrategies(valid_date_of_birth, invalid_date_of_birth),
        "mobile": FieldStrategies(valid_mobile, invalid_mobile),
        "address": FieldStrategies(valid_name_or_address, invalid_name_or_address),
        "state_and_city": FieldStrategies(
            valid_state_and_city(), invalid_state_and_city()
        ),
    }


POSSIBLE_VALUES = possible_values()
STRATEGIES = hypothesis_strategies(POSSIBLE_VALUES)


def fill_form(page: RegistrationFormPage, data: dict[str, Any]):
    select_methods = {
        "gender": page.select_gender,
        "date_of_birth": page.select_date_of_birth,
        "subjects": page.select_subjects,
        "hobbies": page.select_hobbies,
        "state": page.select_state,
        "city": page.select_city,
    }

    for field, value in data.items():
        # If value is None, do nothing
        if value is not None and not page.fields_filled[field]:
            if field in select_methods:
                select_methods[field](value)
            else:
                page.fill_send_keys_field(field, value)
            page.fields_filled[field] = True


# ----------------------------------------------------- SUBMISSION TESTS ------------------------------------------------------


@given(
    first_name=STRATEGIES["first_name"].valid,
    last_name=STRATEGIES["last_name"].valid,
    # Current form validation regexp
    email=st.from_regex(
        re.compile(r"^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$"),
        fullmatch=True,
    ),
    gender_and_picture=STRATEGIES["gender_and_picture"].valid,
    mobile=STRATEGIES["mobile"].valid,
    date_of_birth=STRATEGIES["date_of_birth"].valid,
    subjects=STRATEGIES["subjects"].valid,
    hobbies=STRATEGIES["hobbies"].valid,
    address=STRATEGIES["address"].valid,
    state_and_city=STRATEGIES["state_and_city"].valid,
)
def test_submit_registration_form_with_valid_data(
    registration_page: RegistrationFormPage,
    first_name: str,
    last_name: str,
    email: str,
    gender_and_picture: tuple[str, Path],
    mobile: str,
    date_of_birth: datetime,
    subjects: list[str],
    hobbies: str,
    address: str,
    state_and_city: tuple[str, str],
):
    page = registration_page
    gender, picture = gender_and_picture
    state, city = state_and_city

    data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "gender": gender,
        "mobile": mobile,
        "date_of_birth": date_of_birth,
        "subjects": subjects,
        "hobbies": hobbies,
        "picture": picture,
        "address": address,
        "state": state,
        "city": city,
    }

    fill_form(page, data)

    page.submit()

    is_submitted = page.verify_submission()

    try:
        assert is_submitted, f"Form submission failed with valid {data=}."

        if is_submitted:
            try:
                assert_form_data_matches_expected(page, data)
            finally:
                page.close_modal()
    finally:
        page.reset()


# Verifying that the submitted data matches what's displayed,
# as this confirms the form's functionality rather than its validation correctness
def assert_form_data_matches_expected(
    page: RegistrationFormPage, expected: dict[str, Any]
):
    POPUP_MAP = {
        "Student Name": lambda expected: f"{expected['first_name']} {expected['last_name']}",
        "Student Email": lambda expected: expected["email"],
        "Gender": lambda expected: expected["gender"],
        "Mobile": lambda expected: expected["mobile"],
        "Date of Birth": lambda expected: expected["date_of_birth"].strftime(
            "%d %B,%Y"
        ),
        "Subjects": lambda expected: ", ".join(expected["subjects"]),
        "Hobbies": lambda expected: ", ".join(expected["hobbies"]),
        "Picture": lambda expected: Path(expected["picture"]).name,
        "Address": lambda expected: expected["address"],
        "State and City": lambda expected: f"{expected['state']} {expected['city']}",
    }

    for label, extractor in POPUP_MAP.items():
        expected_value = extractor(expected)
        actual_value = page.get_modal_text(label)
        assert (
            expected_value == actual_value
        ), f"Error {label=}: {expected_value=} {actual_value=}"


# ----------------------------------------------------- VALIDATION TESTS ------------------------------------------------------


def get_test_data(**override_kwargs: dict[str, Any]) -> dict[str, Any]:
    gender = POSSIBLE_VALUES["genders"][0]
    date_of_birth = (datetime.now() - timedelta(days=365.25 * 18)).date()
    valid_state, cities = next(iter(POSSIBLE_VALUES["state_city_map"].items()))
    valid_city = cities[0]

    picture = str(next((PICTURES_DIR / gender).glob("*.jpeg")))

    valid_data = {
        "first_name": "Bob",
        "last_name": "Alice",
        "email": "bob.alice@example.com",
        "gender": gender,
        "mobile": "1234567890",
        "date_of_birth": date_of_birth,
        "subjects": POSSIBLE_VALUES["subjects"][:5],
        "hobbies": POSSIBLE_VALUES["hobbies"],
        "picture": picture,
        "address": "Hazrat Nizamuddin Aulia Dargah, Mathura Rd, Nizamuddin, Nizamuddin East, New Delhi, Delhi 110013, India",
        "state": valid_state,
        "city": valid_city,
    }

    if override_kwargs:
        return {**valid_data, **override_kwargs}
    return valid_data


def field_validation(
    page: RegistrationFormPage, override_values, expect_succes: bool = False
):
    # In case we have the previous test function state
    if any(page.fields_filled.values()):
        page.reset(False)

    data = get_test_data(**override_values)
    fill_form(page, data)
    page.submit()
    is_submitted = page.verify_submission()
    if is_submitted:
        page.close_modal()
        page.unfill_elements()
        page.load_elements(False)
    else:
        for field in override_values:
            try:
                page.clear_field(field)
            except AttributeError:
                # Some fields cannot be cleared, reset the page instead
                page.reset(False)
                break

    if expect_succes:
        assert is_submitted, f"Form submission failed with {override_values=}"
    else:
        assert not is_submitted, f"Form submission succeeded with {override_values=}"


# Each specific test function handles the test logic for a particular field,
# while the base function encapsulates the common validation logic
# The repetition is unavoidable due to the nature of Hypothesis


@given(first_name=STRATEGIES["first_name"].invalid)
def test_first_name_rejection(registration_page, first_name):
    field_validation(registration_page, {"first_name": first_name})


@given(last_name=STRATEGIES["last_name"].invalid)
def test_last_name_rejection(registration_page, last_name):
    field_validation(registration_page, {"last_name": last_name})


@given(email=STRATEGIES["email"].invalid)
def test_email_rejection(registration_page, email):
    field_validation(registration_page, {"email": email})


@given(email=STRATEGIES["email"].valid)
def test_email_acceptance(registration_page, email):
    field_validation(registration_page, {"email": email}, expect_succes=True)


@given(gender=STRATEGIES["gender"].invalid)
def test_gender_rejection(registration_page, gender):
    field_validation(registration_page, {"gender": gender})


@given(picture=STRATEGIES["picture"].invalid)
def test_picture_rejection(registration_page, picture):
    field_validation(registration_page, {"picture": picture})


@given(mobile=STRATEGIES["mobile"].invalid)
def test_mobile_rejection(registration_page, mobile):
    field_validation(registration_page, {"mobile": mobile})


@given(date_of_birth=STRATEGIES["date_of_birth"].invalid)
def test_date_of_birth_rejection(registration_page, date_of_birth):
    field_validation(registration_page, {"date_of_birth": date_of_birth})


@given(subjects=STRATEGIES["subjects"].invalid)
def test_subjects_rejection(registration_page, subjects):
    field_validation(registration_page, {"subjects": subjects})


@given(address=STRATEGIES["address"].invalid)
def test_address_rejection(registration_page, address):
    field_validation(registration_page, {"address": address})


@given(state_and_city=STRATEGIES["state_and_city"].invalid)
def test_state_and_city_rejection(registration_page, state_and_city):
    state, city = state_and_city
    field_validation(registration_page, {"state": state, "city": city})
