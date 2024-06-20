import sys
import os
import string
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QComboBox,
                             QHBoxLayout, QRadioButton, QButtonGroup, QMessageBox, QGridLayout, QFileDialog,
                             QProgressBar)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from pytube import YouTube
import requests
from io import BytesIO
from datetime import datetime


def sanitize_filename(filename):
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    sanitized_filename = ''.join(c for c in filename if c in valid_chars)
    return sanitized_filename


class FetchDetailsThread(QThread):
    details_fetched = pyqtSignal(object)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            yt = YouTube(self.url)
            self.details_fetched.emit(yt)
        except Exception as e:
            self.details_fetched.emit(None)


class DownloadThread(QThread):
    progress = pyqtSignal(int)
    bandwidth = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, stream, output_path, filename):
        super().__init__()
        self.stream = stream
        self.output_path = output_path
        self.filename = filename

    def run(self):
        try:
            # Open a stream to download
            response = requests.get(self.stream.url, stream=True)
            total_size = int(response.headers.get('content-length', 0))

            with open(os.path.join(self.output_path, self.filename), 'wb') as file:
                bytes_downloaded = 0
                start_time = datetime.now()
                for chunk in response.iter_content(chunk_size=1024 * 1024):  # Increased chunk size for faster download
                    if chunk:
                        file.write(chunk)
                        bytes_downloaded += len(chunk)
                        progress = int(bytes_downloaded / total_size * 100)
                        self.progress.emit(progress)

                        # Calculate bandwidth
                        time_elapsed = (datetime.now() - start_time).total_seconds()
                        if time_elapsed > 0:
                            bandwidth = bytes_downloaded / (1024 * 1024 * time_elapsed)  # in Mbps
                            self.bandwidth.emit(f'{bandwidth:.2f} Mbps')

            self.finished.emit()
        except Exception as e:
            print(e)  # Add logging if necessary


class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("YouTube Downloader")
        self.setWindowIcon(QIcon("placeholder_icon.png"))  # Placeholder icon
        self.setGeometry(100, 100, 500, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QGridLayout()
        self.central_widget.setLayout(self.layout)

        self.initUI()

    def initUI(self):
        # Logo
        self.logo = QLabel(self)
        pixmap = QPixmap("placeholder_logo.png")  # Placeholder logo
        self.logo.setPixmap(pixmap)
        self.logo.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.logo, 0, 0, 1, 2)

        # Input box for video URL
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Enter YouTube video URL")
        self.url_input.returnPressed.connect(self.fetch_video_details)
        self.layout.addWidget(self.url_input, 1, 0, 1, 2)

        # Video thumbnail
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.thumbnail_label, 2, 0, 1, 2)

        # Format selection
        self.format_group = QButtonGroup(self)

        self.audio_radio = QRadioButton("Audio", self)
        self.video_radio = QRadioButton("Video", self)
        self.format_group.addButton(self.audio_radio)
        self.format_group.addButton(self.video_radio)
        self.layout.addWidget(self.audio_radio, 3, 0)
        self.layout.addWidget(self.video_radio, 3, 1)

        self.audio_radio.toggled.connect(self.toggle_format_selection)

        # Audio bitrate selection
        self.bitrate_label = QLabel("Select Bitrate:", self)
        self.bitrate_combo = QComboBox(self)
        self.layout.addWidget(self.bitrate_label, 4, 0)
        self.layout.addWidget(self.bitrate_combo, 4, 1)

        # Video quality selection
        self.quality_label = QLabel("Select Quality:", self)
        self.quality_combo = QComboBox(self)
        self.layout.addWidget(self.quality_label, 5, 0)
        self.layout.addWidget(self.quality_combo, 5, 1)

        # Output folder selection
        self.output_folder_label = QLabel("Output Folder:", self)
        self.output_folder_button = QPushButton("Choose Folder", self)
        self.output_folder_button.clicked.connect(self.choose_output_folder)
        self.layout.addWidget(self.output_folder_label, 6, 0)
        self.layout.addWidget(self.output_folder_button, 6, 1)

        # Download button
        self.download_button = QPushButton("Download", self)
        self.download_button.clicked.connect(self.download_video)
        self.layout.addWidget(self.download_button, 7, 0, 1, 2)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.layout.addWidget(self.progress_bar, 8, 0, 1, 2)

        # Bandwidth label
        self.bandwidth_label = QLabel("Bandwidth: 0.00 Mbps", self)
        self.layout.addWidget(self.bandwidth_label, 9, 0, 1, 2)

        # Hide bitrate and quality selection initially
        self.bitrate_label.hide()
        self.bitrate_combo.hide()
        self.quality_label.hide()
        self.quality_combo.hide()
        self.output_folder_label.hide()
        self.output_folder_button.hide()
        self.progress_bar.hide()
        self.bandwidth_label.hide()

        # Apply a modern stylesheet
        self.setStyleSheet("""
            QWidget {
                font-family: Arial;
                font-size: 14px;
            }
            QLineEdit, QComboBox, QPushButton {
                padding: 10px;
                margin: 5px 0;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QRadioButton {
                margin: 10px 0;
            }
            QProgressBar {
                border: 1px solid #3498db;
                border-radius: 5px;
                text-align: center;
                margin-top: 10px;
            }
        """)

    def toggle_format_selection(self):
        if self.audio_radio.isChecked():
            self.bitrate_label.show()
            self.bitrate_combo.show()
            self.quality_label.hide()
            self.quality_combo.hide()
        elif self.video_radio.isChecked():
            self.bitrate_label.hide()
            self.bitrate_combo.hide()
            self.quality_label.show()
            self.quality_combo.show()

    def fetch_video_details(self):
        url = self.url_input.text()
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a YouTube video URL.")
            return

        self.fetch_thread = FetchDetailsThread(url)
        self.fetch_thread.details_fetched.connect(self.on_details_fetched)
        self.fetch_thread.start()

    @pyqtSlot(object)
    def on_details_fetched(self, yt):
        if yt is None:
            QMessageBox.critical(self, "Error", "Failed to fetch video details.")
            return

        self.yt = yt
        self.thumbnail_url = self.yt.thumbnail_url

        # Fetch and display thumbnail
        response = requests.get(self.thumbnail_url)
        image = QPixmap()
        image.loadFromData(BytesIO(response.content).read())
        self.thumbnail_label.setPixmap(image.scaled(320, 180, Qt.KeepAspectRatio))

        # Populate audio bitrate options
        self.bitrate_combo.clear()
        audio_streams = self.yt.streams.filter(only_audio=True)
        for stream in audio_streams:
            self.bitrate_combo.addItem(f"{stream.abr} kbps")

        # Populate video quality options
        self.quality_combo.clear()
        video_streams = self.yt.streams.filter(file_extension='mp4').order_by('resolution')
        resolutions = []
        for stream in video_streams:
            if stream.resolution not in resolutions:
                resolutions.append(stream.resolution)
                self.quality_combo.addItem(f"{stream.resolution} - {stream.fps}fps")

        # Enable output folder selection
        self.output_folder_label.show()
        self.output_folder_button.show()

        # Select default options
        self.audio_radio.setChecked(True)
        self.toggle_format_selection()

        QMessageBox.information(self, "Success", "Video details fetched successfully.")

    def choose_output_folder(self):
        options = QFileDialog.Options()
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", options=options)
        if folder:
            self.output_folder = folder
            self.output_folder_label.setText(f"Output Folder: {folder}")

    def download_video(self):
        if self.audio_radio.isChecked():
            self.download_audio()
        elif self.video_radio.isChecked():
            self.download_video_file()

    def download_audio(self):
        try:
            selected_bitrate = self.bitrate_combo.currentText().split(" ")[0]
            stream = self.yt.streams.filter(only_audio=True, abr=f"{selected_bitrate}").first()
            if stream:
                filename = f"{sanitize_filename(self.yt.title)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                self.start_download(stream, filename)
            else:
                QMessageBox.critical(self, "Error", "Selected audio stream not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to download audio: {e}")

    def download_video_file(self):
        try:
            selected_quality = self.quality_combo.currentText().split(" - ")[0]
            stream = self.yt.streams.filter(res=selected_quality, file_extension='mp4').first()
            if stream:
                filename = f"{sanitize_filename(self.yt.title)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                self.start_download(stream, filename)
            else:
                QMessageBox.critical(self, "Error", "Selected video stream not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to download video: {e}")

    def start_download(self, stream, filename):
        self.download_thread = DownloadThread(stream, self.output_folder, filename)
        self.download_thread.progress.connect(self.progress_bar.setValue)
        self.download_thread.bandwidth.connect(self.bandwidth_label.setText)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.start()

        self.progress_bar.show()
        self.bandwidth_label.show()

    @pyqtSlot()
    def on_download_finished(self):
        QMessageBox.information(self, "Success", "Download completed successfully.")
        self.progress_bar.hide()
        self.bandwidth_label.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeDownloader()
    window.show()
    sys.exit(app.exec_())
