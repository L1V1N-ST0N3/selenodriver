from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .exceptions import NoSuchElementException
from .element import WebElement


def title_is(title: str):
    def _predicate(driver: Any):
        return driver.title == title

    return _predicate


def title_contains(title: str):
    def _predicate(driver: Any):
        return title in driver.title

    return _predicate


def url_contains(url: str):
    def _predicate(driver: Any):
        return url in driver.current_url

    return _predicate


def url_to_be(url: str):
    def _predicate(driver: Any):
        return driver.current_url == url

    return _predicate


def url_matches(pattern: str):
    def _predicate(driver: Any):
        return re.search(pattern, driver.current_url) is not None

    return _predicate


def url_changes(url: str):
    def _predicate(driver: Any):
        return driver.current_url != url

    return _predicate


def presence_of_element_located(locator: tuple[str, str]):
    def _predicate(driver: Any):
        try:
            return driver.find_element(*locator)
        except NoSuchElementException:
            return False

    return _predicate


def presence_of_all_elements_located(locator: tuple[str, str]):
    def _predicate(driver: Any):
        elements = driver.find_elements(*locator)
        return elements if elements else False

    return _predicate


def visibility_of_element_located(locator: tuple[str, str]):
    def _predicate(driver: Any):
        try:
            element = driver.find_element(*locator)
            return _element_if_visible(element)
        except NoSuchElementException:
            return False

    return _predicate


def visibility_of(element: WebElement):
    def _predicate(_driver: Any):
        return _element_if_visible(element)

    return _predicate


def visibility_of_any_elements_located(locator: tuple[str, str]):
    def _predicate(driver: Any):
        elements = driver.find_elements(*locator)
        visible = [element for element in elements if element.is_displayed()]
        return visible if visible else False

    return _predicate


def visibility_of_all_elements_located(locator: tuple[str, str]):
    def _predicate(driver: Any):
        elements = driver.find_elements(*locator)
        if not elements:
            return False
        return elements if all(element.is_displayed() for element in elements) else False

    return _predicate


def invisibility_of_element_located(locator: tuple[str, str]):
    def _predicate(driver: Any):
        try:
            element = driver.find_element(*locator)
            return not element.is_displayed()
        except NoSuchElementException:
            return True

    return _predicate


def invisibility_of_element(element: WebElement):
    def _predicate(_driver: Any):
        try:
            return not element.is_displayed()
        except NoSuchElementException:
            return True

    return _predicate


def element_to_be_clickable(mark: tuple[str, str] | WebElement):
    def _predicate(driver: Any):
        try:
            element = driver.find_element(*mark) if isinstance(mark, tuple) else mark
            return element if element.is_displayed() and element.is_enabled() else False
        except NoSuchElementException:
            return False

    return _predicate


def element_to_be_selected(element: WebElement):
    def _predicate(_driver: Any):
        return element.is_selected()

    return _predicate


def element_located_to_be_selected(locator: tuple[str, str]):
    def _predicate(driver: Any):
        try:
            return driver.find_element(*locator).is_selected()
        except NoSuchElementException:
            return False

    return _predicate


def element_selection_state_to_be(element: WebElement, is_selected: bool):
    def _predicate(_driver: Any):
        return element.is_selected() is bool(is_selected)

    return _predicate


def element_located_selection_state_to_be(locator: tuple[str, str], is_selected: bool):
    def _predicate(driver: Any):
        try:
            return driver.find_element(*locator).is_selected() is bool(is_selected)
        except NoSuchElementException:
            return False

    return _predicate


def frame_to_be_available_and_switch_to_it(locator: Any):
    def _predicate(driver: Any):
        try:
            frame = driver.find_element(*locator) if isinstance(locator, tuple) else locator
            driver.switch_to.frame(frame)
            return True
        except Exception:
            return False

    return _predicate


def text_to_be_present_in_element(locator: tuple[str, str], text_: str):
    def _predicate(driver: Any):
        try:
            return text_ in driver.find_element(*locator).text
        except NoSuchElementException:
            return False

    return _predicate


def text_to_be_present_in_element_attribute(locator: tuple[str, str], attribute_: str, text_: str):
    def _predicate(driver: Any):
        try:
            value = driver.find_element(*locator).get_attribute(attribute_)
            return value is not None and text_ in value
        except NoSuchElementException:
            return False

    return _predicate


def text_to_be_present_in_element_value(locator: tuple[str, str], text_: str):
    return text_to_be_present_in_element_attribute(locator, "value", text_)


def element_attribute_to_include(locator: tuple[str, str], attribute_: str):
    def _predicate(driver: Any):
        try:
            return driver.find_element(*locator).get_attribute(attribute_) is not None
        except NoSuchElementException:
            return False

    return _predicate


def number_of_windows_to_be(num_windows: int):
    def _predicate(driver: Any):
        return len(driver.window_handles) == num_windows

    return _predicate


def new_window_is_opened(current_handles: Iterable[str]):
    handles = set(current_handles)

    def _predicate(driver: Any):
        return len(set(driver.window_handles) - handles) > 0

    return _predicate


def alert_is_present():
    def _predicate(driver: Any):
        try:
            return driver.switch_to.alert
        except Exception as error:
            from .exceptions import NoAlertPresentException

            if isinstance(error, NoAlertPresentException):
                return False
            raise

    return _predicate


def staleness_of(element: WebElement):
    def _predicate(_driver: Any):
        try:
            element.is_enabled()
            return False
        except Exception:
            return True

    return _predicate


def any_of(*expected_conditions):
    def _predicate(driver: Any):
        for condition in expected_conditions:
            try:
                result = condition(driver)
                if result:
                    return result
            except Exception:
                pass
        return False

    return _predicate


def all_of(*expected_conditions):
    def _predicate(driver: Any):
        results = []
        for condition in expected_conditions:
            try:
                result = condition(driver)
                if not result:
                    return False
                results.append(result)
            except Exception:
                return False
        return results

    return _predicate


def none_of(*expected_conditions):
    def _predicate(driver: Any):
        for condition in expected_conditions:
            try:
                if condition(driver):
                    return False
            except Exception:
                pass
        return True

    return _predicate


def _element_if_visible(element: WebElement):
    return element if element.is_displayed() else False
