# Required Dependencies:
# - PyQt5: For building the GUI
# - Selenium: For browser automation
# - Webdriver_Manager: To manage ChromeDriver versions automatically
# - csv, re, datetime, time: For handling data storage and processing
# Install using pip:
# > pip install pyqt5 selenium webdriver-manager

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QRadioButton, QButtonGroup,
    QSpinBox, QPushButton, QFileDialog, QVBoxLayout, QWidget, QMessageBox
)
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import re
from datetime import datetime

"""
Google Play Review Scraper

A GUI-based application that scrapes reviews from Google Play Store using Selenium and PyQt5.

Features:
- Extracts reviews in Korean or English
- Saves results to a CSV file
- User-friendly interface with input controls
- Error handling for invalid inputs

Limitations:
- Relies on browser automation, which may break if Google Play changes its HTML structure
- May require manual adjustments for different devices/screens
"""

class ScraperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Google Play Review Scraper")
        self.setGeometry(100, 100, 600, 300)

        # Main layout
        layout = QVBoxLayout()

        # Play Store Link
        self.link_label = QLabel("Play Store Link:")
        self.link_input = QLineEdit()
        layout.addWidget(self.link_label)
        layout.addWidget(self.link_input)

        # Language Selection
        self.lang_label = QLabel("Language:")
        self.kr_radio = QRadioButton("Korean (KR)")
        self.us_radio = QRadioButton("English (US)")
        self.kr_radio.setChecked(True)
        self.lang_group = QButtonGroup()
        self.lang_group.addButton(self.kr_radio)
        self.lang_group.addButton(self.us_radio)
        layout.addWidget(self.lang_label)
        layout.addWidget(self.kr_radio)
        layout.addWidget(self.us_radio)

        # Tab Count
        self.tab_label = QLabel("Tab Count:")
        self.tab_input = QSpinBox()
        self.tab_input.setValue(1000)
        self.tab_input.setMaximum(10000)
        layout.addWidget(self.tab_label)
        layout.addWidget(self.tab_input)

        # Output File
        self.output_button = QPushButton("Select Output File")
        self.output_button.clicked.connect(self.select_output_file)
        self.output_file = None
        layout.addWidget(self.output_button)

        # Run Button
        self.run_button = QPushButton("Run Scraper")
        self.run_button.clicked.connect(self.run_scraper)
        layout.addWidget(self.run_button)

        # Set central widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def select_output_file(self):
        self.output_file, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        if self.output_file:
            QMessageBox.information(self, "File Selected", f"Output file: {self.output_file}")

    def run_scraper(self):
        link = self.link_input.text()
        is_kr = self.kr_radio.isChecked()
        tab_count = self.tab_input.value()

        if not link or not self.output_file:
            QMessageBox.warning(self, "Error", "Please provide all inputs.")
            return

        try:
            self.extract_reviews(link, is_kr, tab_count, self.output_file)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def extract_reviews(self, link, is_kr, tab_count, output_file):
        # Setup Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            # Go to App Page
            driver.get(link)
            time.sleep(3)

            # Click the 3rd 'arrow_forward' icon
            arrow_icons = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//i[text()="arrow_forward"]'))
            )
            if len(arrow_icons) >= 3:
                arrow_button = arrow_icons[2].find_element(By.XPATH, './ancestor::button')
                arrow_button.click()
                time.sleep(3)
            else:
                raise Exception("Not enough arrow buttons found.")

            # Simulate Tab presses to load more reviews
            body = driver.find_element(By.TAG_NAME, "body")
            for i in range(tab_count):
                body.send_keys(Keys.TAB)
                time.sleep(0.01)

            time.sleep(3)

            # Extract all reviews
            reviews = driver.find_elements(By.CLASS_NAME, "RHo1pe")
            extracted = []

            for review in reviews:
                try:
                    review_text = review.find_element(By.CLASS_NAME, "h3YV2d").text.strip()

                    # Meta section
                    meta = review.find_element(By.CLASS_NAME, "Jx4nYe")

                    # Rating
                    rating_div = meta.find_element(By.CSS_SELECTOR, 'div[role="img"]')
                    aria_label = rating_div.get_attribute("aria-label")
                    if is_kr:
                        match = re.search(r'(\d+)개를 받았습니다', aria_label)
                    else:
                        match = re.search(r'Rated (\d+) stars', aria_label)
                    rating = int(match.group(1)) if match else None

                    # Date
                    date = meta.find_element(By.CLASS_NAME, "bp9Aid").text.strip()

                    if is_kr:
                        # Extract first 3 numbers and format to MM-DD-YYYY
                        nums = re.findall(r'\d+', date)
                        if len(nums) >= 3:
                            year, month, day = nums[:3]
                            date = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
                    else:
                        # Convert US format to 'YYYY-MM-DD' (or change to MM-DD-YYYY if preferred)
                        date = datetime.strptime(date, "%B %d, %Y").strftime("%Y-%m-%d")

                    extracted.append({
                        "review": review_text,
                        "rating": rating,
                        "date": date
                    })

                except Exception:
                    continue

            # Save to CSV
            extracted = sorted(extracted, key=lambda x: x['date'])

            with open(output_file, mode="w", encoding="utf-8-sig", newline='') as file:
                writer = csv.DictWriter(file, fieldnames=["review", "rating", "date"])
                writer.writeheader()
                writer.writerows(extracted)

            QMessageBox.information(self, "Success", f"Saved {len(extracted)} reviews to {output_file}")

        except Exception as e:
            raise e

        finally:
            driver.quit()

# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScraperApp()
    window.show()
    sys.exit(app.exec_())