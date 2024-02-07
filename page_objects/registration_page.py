import datetime

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class RegistrationFormPage:
    def __init__(self, driver):
        self.driver = driver
        self.load_elements()
        self.fields_filled = {
            field: False
            for field in [
                "first_name",
                "last_name",
                "email",
                "gender",
                "picture",
                "mobile",
                "date_of_birth",
                "subjects",
                "hobbies",
                "address",
                "state",
                "city",
            ]
        }

    def unfill_elements(self):
        for field in self.fields_filled:
            self.fields_filled[field] = False

    def reset(self):
        self.driver.refresh()
        self.unfill_elements()
        # self.driver.delete_all_cookies()
        # self.driver.execute_script("window.localStorage.clear();")
        # self.driver.execute_script("window.sessionStorage.clear();")
        self.load_elements()

    def load_elements(self, accept_consent=True):
        if accept_consent:
            self.accept_consent_if_present()
        self.alphabet = "abcdefghijklmnopqrstuvwxyz"
        self.first_name = self.driver.find_element(By.CSS_SELECTOR, "input#firstName")
        self.last_name = self.driver.find_element(By.CSS_SELECTOR, "input#lastName")
        self.email = self.driver.find_element(By.ID, "userEmail")
        self.mobile = self.driver.find_element(By.CSS_SELECTOR, "input#userNumber")
        self.date_of_birth = self.driver.find_element(By.ID, "dateOfBirthInput")
        self.picture = self.driver.find_element(By.CSS_SELECTOR, "input#uploadPicture")
        self.subjects = self.driver.find_element(
            By.CSS_SELECTOR,
            "input#subjectsInput",
        )
        self.address = self.driver.find_element(
            By.CSS_SELECTOR, "textarea#currentAddress"
        )
        self.dropdown_options_xpath = (
            ".//div[contains(@class, 'menu')]/div/div[contains(@id, 'option')]"
        )
        self.state = self.driver.find_element(
            By.CSS_SELECTOR, "#state input[type='text']"
        )
        self.city = self.driver.find_element(
            By.CSS_SELECTOR, "#city input[type='text']"
        )
        self.submit_button = self.driver.find_element(By.CSS_SELECTOR, "#submit")

    def accept_consent_if_present(self, timeout: float = 1.0):
        try:
            consent_button = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.fc-cta-consent.fc-primary-button")
                )
            )
            consent_button.click()
        except (TimeoutException, NoSuchElementException):
            # No consent button found or not clickable within timeout
            pass

    def fill_send_keys_field(self, field_name: str, value: str):
        field = getattr(self, field_name)
        field.send_keys(value)

    def clear_field(self, field_name: str):
        field = getattr(self, field_name)
        field.clear()
        self.fields_filled[field_name] = False

    def scrape_genders(self) -> list[str]:
        return [
            element.text
            for element in self.driver.find_elements(
                By.CSS_SELECTOR, "#genterWrapper label.custom-control-label"
            )
        ]

    def select_gender(self, gender: str):
        gender_map = {
            "Male": "label[for='gender-radio-1']",
            "Female": "label[for='gender-radio-2']",
            "Other": "label[for='gender-radio-3']",
        }

        if gender in gender_map:
            element = self.driver.find_element(By.CSS_SELECTOR, gender_map[gender])
            element.click()

    def scrape_hobbies(self) -> list[str]:
        return [
            element.text
            for element in self.driver.find_elements(
                By.CSS_SELECTOR, "#hobbiesWrapper .custom-control-label"
            )
        ]

    def select_hobbies(self, hobbies: list[str]):
        hobby_map = {
            "Sports": "label[for='hobbies-checkbox-1']",
            "Reading": "label[for='hobbies-checkbox-2']",
            "Music": "label[for='hobbies-checkbox-3']",
        }

        for hobby in hobbies:
            if hobby in hobby_map:
                element = self.driver.find_element(By.CSS_SELECTOR, hobby_map[hobby])
                element.click()

    def __select_date_component(self, selector: str, value: str, timeout: float = 2):
        WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, selector))
        ).send_keys(value)

    def select_date_of_birth(self, date: datetime.datetime, timeout: float = 3):
        WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(self.date_of_birth)
        ).click()
        self.__select_date_component(
            "//select[@class='react-datepicker__year-select']", date.year
        )
        self.__select_date_component(
            "//select[@class='react-datepicker__month-select']", date.strftime("%B")
        )
        day_xpath = f"//div[contains(@class,'react-datepicker__day') and not(contains(@class,'react-datepicker__day--outside-month')) and text()='{date.day}']"
        self.driver.find_element(By.XPATH, day_xpath).click()

    def scrape_dropdown_with_alphabet(self, element: WebElement):
        res = set()
        for letter in self.alphabet:
            element.send_keys(letter)
            dropdown_options = self.driver.find_elements(
                By.XPATH, self.dropdown_options_xpath
            )
            if dropdown_options:
                res.update(el.text for el in dropdown_options)
            element.clear()
        return sorted(res)

    def select_from_dropdown(self, element: WebElement, option: str):
        element.send_keys(option)
        option = self.driver.find_element(
            By.XPATH, f"{self.dropdown_options_xpath}[contains(., '{option}')]"
        )
        option.click()

    def scrape_subjects(self) -> list[str]:
        return self.scrape_dropdown_with_alphabet(self.subjects)

    def select_subjects(self, subjects: list[str]):
        for subject in subjects:
            self.select_from_dropdown(self.subjects, subject)

    def scrape_states_and_cities(self) -> dict[str, list[str]]:
        state_city_map = {}

        states = self.scrape_dropdown_with_alphabet(self.state)

        for state in states:
            self.select_state(state)
            state_city_map[state] = self.scrape_dropdown_with_alphabet(self.city)
            self.state.clear()

        return state_city_map

    def select_state(self, state: str):
        self.select_from_dropdown(self.state, state)

    def select_city(self, city: str):
        self.select_from_dropdown(self.city, city)

    def submit(self):
        self.submit_button.click()

    def verify_submission(self, timeout: float = 1) -> bool:
        modal_title_xpath = "//div[@class='modal-title h4' and contains(text(), 'Thanks for submitting the form')]"
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.XPATH, modal_title_xpath))
            )
            self.driver.find_element(By.CSS_SELECTOR, "#closeLargeModal").click()
        except (TimeoutException, NoSuchElementException):
            return False

        return True

    def get_modal_text(self, label: str) -> str:
        xpath = f"//td[text()='{label}']/following-sibling::td"
        return self.driver.find_element(By.XPATH, xpath).text
