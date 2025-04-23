import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QTextEdit, QFileDialog, QLineEdit)
import pandas as pd
import re  # For potential regex parsing of LLM output
from datetime import datetime
import requests

class DoctorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Google Play Review UI/UX Insight Generator")
        self.setGeometry(100, 100, 800, 600)  # Larger window for insights

        layout = QVBoxLayout()

        # File Selection Button
        self.file_button = QPushButton("Select CSV File")
        self.file_button.clicked.connect(self.select_csv_file)
        self.csv_file = None
        layout.addWidget(self.file_button)

        # Prompt Input
        self.prompt_label = QLabel("Enter Custom Prompt:")
        self.prompt_input = QLineEdit()
        layout.addWidget(self.prompt_label)
        layout.addWidget(self.prompt_input)

        # Analyze Button
        self.analyze_button = QPushButton("Analyze Reviews")
        self.analyze_button.clicked.connect(self.analyze_reviews)
        self.analyze_button.setEnabled(False)  # Disable until file is selected
        layout.addWidget(self.analyze_button)

        # Output Text Area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # LM Studio Configuration
        self.lmstudio_api_url = "http://127.0.0.1:1234/v1/completions"  # Adjust if different
        self.model_identifier = "gemma-3-27b-it-qat" # Your LM Studio model identifier
        self.chunk_size = 20  # Number of reviews per chunk - tune this!
        self.language = 'EN'

    def select_csv_file(self):
        self.csv_file, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if self.csv_file:
            self.analyze_button.setEnabled(True)  # Enable analyze button

    def analyze_reviews(self):
        try:
            df = pd.read_csv(self.csv_file, encoding='utf-8') # Added encoding
            self.generate_insights(df)
        except Exception as e:
            self.output_text.setText(f"Error loading or analyzing CSV file: {e}")

    def generate_insights(self, df):
        # Check if 'review' column exists
        if 'review' not in df.columns:
            self.output_text.setText("Error: 'review' column not found in the CSV file.")
            return

        insights = ""
        all_reviews = df['review'].tolist()
        num_reviews = len(all_reviews)
        chunk_reports = []  # Store reports from each chunk

        for i in range(0, num_reviews, self.chunk_size):
            chunk = all_reviews[i:i + self.chunk_size]
            normalized_chunk = [self.normalize_text(review) for review in chunk]  # Normalize each review
            prompt = f"""{self.prompt_input.text()} Reviews: {normalized_chunk}"""

            try:
                response = self.call_lmstudio(prompt)
                chunk_reports.append(response) # Store the report from this chunk
                insights += response + "\n\n"  # Append LLM output for immediate feedback
            except Exception as e:
                self.output_text.setText(f"Error calling LM Studio API: {e}")
                return

        # Final Report Aggregation and Trimming
        final_prompt = f"""Combine the following UI/UX reports from Google Play Store review analysis into a single, concise list of actionable insights.  Prioritize the most important issues (maximum 5). Remove redundant information. I do NOT want code or rambling in the response.
        Reports: {chunk_reports}"""

        try:
            final_response = self.call_lmstudio(final_prompt)
            self.output_text.setText(f"Final Report:\n{final_response}")
        except Exception as e:
            self.output_text.setText(f"Error generating final report: {e}")

    def call_lmstudio(self, prompt):
        """Calls the LM Studio API using the /v1/completions endpoint."""

        payload = {
            "model": self.model_identifier,
            "prompt": prompt,
            "max_tokens": 500,  # Reduced max tokens for chunk reports
            "temperature": 0.7
        }

        try:
            response = requests.post(self.lmstudio_api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            print("API Response:", data)  # Add this line for debugging
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['text']
            else:
                return "No content returned from model."
        except requests.exceptions.RequestException as e:
            raise Exception(f"LM Studio API request failed: {e}")

    def normalize_text(self, text):
        """Normalizes review text before sending to the LLM, compatible with Korean."""
        if isinstance(text, float):  # Handle NaN values in the DataFrame
            return ""

        text = str(text) #ensure it's a string.

        if self.language == 'KR':
            text = re.sub(r'[^\uAC00-\uD7A3\w\s.,!?]', '', text)  # Unicode range for Hangul syllables
        else:
            text = re.sub(r'[^a-zA-Z0-9\w\s.,!?]', '', text)

        text = ' '.join(text.split())

        return text

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DoctorApp()
    window.show()


    # Optional: test LLM call directly before GUI loop
    test_prompt = "Are you a real human being?"
    try:
        response = window.call_lmstudio(test_prompt)
        print("LLM Response:", response)
    except Exception as e:
        print("Test call failed:", e)

    sys.exit(app.exec_())
