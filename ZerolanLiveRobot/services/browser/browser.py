from selenium.webdriver import Firefox, Chrome, Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from services.browser.config import BrowserConfig
from services.browser import driver
from services.browser.driver import DriverInitializer

_SEARCH_BOX_SELECTORS = [
    (By.ID, "sb_form_q"),           # Bing
    (By.NAME, "q"),                 # Google, DuckDuckGo, Baidu
    (By.CSS_SELECTOR, "input[type='search']"),
    (By.CSS_SELECTOR, "input[role='searchbox']"),
    (By.CSS_SELECTOR, "textarea[name='q']"),  # Google homepage
]


class Browser:
    def __init__(self, config: BrowserConfig):
        self._initzr = DriverInitializer(config)
        self._driver: Firefox | Chrome | None = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = self._initzr.get_driver()
        return self._driver

    def open(self, url: str):
        self.driver.get(url)

    def close(self):
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    def page_source(self):
        return self.driver.page_source

    def _find_search_box(self):
        for by, value in _SEARCH_BOX_SELECTORS:
            try:
                element = self.driver.find_element(by, value)
                if element.is_displayed():
                    return element
            except NoSuchElementException:
                continue
        return None

    def search(self, text: str):
        search_box = self._find_search_box()
        if search_box is None:
            raise NoSuchElementException(
                "Could not find a search box on the current page."
            )
        search_box.click()
        search_box.clear()
        search_box.send_keys(text)
        search_box.send_keys(Keys.ENTER)

    def __del__(self):
        self.close()
