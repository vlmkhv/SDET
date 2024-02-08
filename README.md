# Automated Form Testing

This project automates form testing on a [demo website](https://demoqa.com/automation-practice-form) using Selenium WebDriver. It focuses on validating form submissions, handling various input fields, and ensuring the form behaves as expected under different scenarios.

## Features

- **Page Object Model**: Implements the Page Object Model (POM) pattern for better maintainability and readability.
- **Dynamic Data Handling**: Uses Hypothesis for generating a wide range of test data, covering both valid and invalid cases.
- **State Management**: Manages the state of form fields to optimize test execution, avoiding unnecessary form resets and data re-entry.
- **Comprehensive Validation**: Includes tests for all form fields, including name, email, gender selection, date of birth, subjects, hobbies, address, state, and city.
- **Modular Structure**: Organized code structure with separate modules for page objects, test data generation, and utility functions.

## Setup

1. **Clone repository** 
2. **Dependencies**: Install required Python packages using `pip install -r requirements.txt`.

## Running Tests

Execute the tests using pytest:

```sh
pytest test_registration.py
```

## Customization

- **Test Data**: Modify the `hypothesis_strategies` function to adjust the generated test data.
- **Form Fields**: Update the `RegistrationFormPage` class to match the form fields of your target webpage.

For more details on each component and how to extend the testing suite, refer to the inline comments and documentation within the code files.