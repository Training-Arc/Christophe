from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
import sys
import os
import librosa
from moviepy.editor import VideoFileClip
import threading
from collections import deque
import cv2

class Playhead(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(3)
        self.setMaximumWidth(3)
        self.setStyleSheet("background-color: red;")
        self.setMouseTracking(True)
        self.dragging = False
        self.pixel_per_second = 10
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.movePlayhead)
        self.position = 0  # Track the position in seconds

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.timer.stop()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            cursor_position = event.globalX()
            parent_position = self.parent().mapToGlobal(self.parent().pos())
            new_x = cursor_position - parent_position.x()
            if 0 <= new_x <= self.parent().width():
                self.move(int(new_x), self.y())
                self.position = new_x / self.pixel_per_second  # Update position in seconds
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        event.accept()

    def movePlayhead(self):
        if not self.dragging:
            new_x = int(self.position * self.pixel_per_second + self.pixel_per_second / 10)
            if new_x <= self.parent().width():
                self.position += 0.1  # Move the position by 0.1 seconds
                self.move(int(self.position * self.pixel_per_second), self.y())
            else:
                self.timer.stop()

    def updatePixelPerSecond(self, pixel_per_second):
        self.pixel_per_second = pixel_per_second
        self.updatePosition(self.position)  # Ensure playhead is updated with new scaling

    def updatePosition(self, position):
        self.position = position
        new_x = int(self.position * self.pixel_per_second)
        self.move(new_x, self.y())

    def updatePlayheadFromVideoPosition(self, video_position):
        self.position = video_position
        self.updatePosition(self.position)


class VideoTimelineWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, bottom_half_widget=None, file_name="", start_time=0):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setSpacing(0)  # Reduce space between widgets
        self.setLayout(self.layout)
        self.setFixedHeight(60)
        self.duration = 0
        self.pixel_per_second = 10
        self.video_loaded = False
        self.file_name = file_name  # Track the file name
        self.bottom_half_widget = bottom_half_widget
        self.cuts = []
        self.selected = False
        self.start_time = start_time
        self.setAcceptDrops(True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)

    def addCut(self, position):
        self.cuts.append(position)
        self.update()

    def splitSegment(self, position):
        segment1 = VideoTimelineWidget(self.parent(), self.bottom_half_widget, self.file_name, self.start_time)
        segment2 = VideoTimelineWidget(self.parent(), self.bottom_half_widget, self.file_name, self.start_time + position)
        segment1.duration = position
        segment2.duration = self.duration - position
        segment1.pixel_per_second = self.pixel_per_second
        segment2.pixel_per_second = self.pixel_per_second
        segment1.setMinimumWidth(int(segment1.duration * self.pixel_per_second))
        segment2.setMinimumWidth(int(segment2.duration * self.pixel_per_second))
        segment1.update()
        segment2.update()
        return segment1, segment2

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        total_width = int(self.duration * self.pixel_per_second)
        painter.setBrush(QtGui.QColor(70, 130, 180))

        start_x = 0
        for cut in sorted(self.cuts):
            cut_x = int(cut * self.pixel_per_second)
            self.drawSegment(painter, start_x, cut_x - 2)  # Add space between segments
            start_x = cut_x + 2  # Move start_x to next position with space

        self.drawSegment(painter, start_x, total_width)

        # Draw the file name
        painter.setPen(QtCore.Qt.white)
        painter.drawText(10, 30, self.file_name)

        if self.selected:
            painter.setBrush(QtGui.QColor(0, 0, 255, 128))
            painter.drawRoundedRect(0, 0, total_width, self.height(), 10, 10)

    def drawSegment(self, painter, start_x, end_x):
        width = end_x - start_x
        if width > 0:
            painter.drawRoundedRect(start_x, 0, width, self.height(), 10, 10)

    def updateDuration(self, duration, file_name=""):
        self.duration = duration
        self.file_name = file_name  # Update the file name
        self.setMinimumWidth(int(self.duration * self.pixel_per_second))
        self.video_loaded = True
        self.update()

    def updatePixelPerSecond(self, pixel_per_second):
        self.pixel_per_second = pixel_per_second
        self.setMinimumWidth(int(self.duration * self.pixel_per_second))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.bottom_half_widget.cuttingMode:
            cut_position = event.pos().x() / self.pixel_per_second
            self.addCut(cut_position)
            self.bottom_half_widget.addCutToPair(self, cut_position)
        else:
            self.selected = not self.selected
            self.update()
            print("VideoTimelineWidget clicked at position:", event.pos())

    def mouseMoveEvent(self, event):
        if self.bottom_half_widget.cuttingMode:
            self.bottom_half_widget.handleMouseMove(event)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.bottom_half_widget.cuttingMode:
            self.bottom_half_widget.handleLeaveEvent(event)
        super().leaveEvent(event)


class AudioWaveformWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, file_name="", start_time=0):
        super().__init__(parent)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setSpacing(0)  # Reduce space between widgets
        self.setLayout(self.layout)
        self.setFixedHeight(60)
        self.duration = 0
        self.pixel_per_second = 10
        self.audio_data = None
        self.cuts = []
        self.selected = False
        self.file_name = file_name  # Track the file name
        self.start_time = start_time
        self.setMouseTracking(True)
        self.volume_scale = 5.0  # Default scale for audio volume

    def set_volume_scale(self, scale):
        self.volume_scale = scale
        self.update()

    def addCut(self, position):
        self.cuts.append(position)
        self.update()

    def splitSegment(self, position):
        segment1 = AudioWaveformWidget(self.parent(), self.file_name, self.start_time)
        segment2 = AudioWaveformWidget(self.parent(), self.file_name, self.start_time + position)
        segment1.duration = position
        segment2.duration = self.duration - position
        segment1.pixel_per_second = self.pixel_per_second
        segment2.pixel_per_second = self.pixel_per_second
        segment1.audio_data = self.audio_data[:int(len(self.audio_data) * (position / self.duration))]
        segment2.audio_data = self.audio_data[int(len(self.audio_data) * (position / self.duration)):]
        segment1.setMinimumWidth(int(segment1.duration * self.pixel_per_second))
        segment2.setMinimumWidth(int(segment2.duration * self.pixel_per_second))
        segment1.update()
        segment2.update()
        return segment1, segment2

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtCore.Qt.NoPen)
        total_width = int(self.duration * self.pixel_per_second)
        painter.setBrush(QtGui.QColor(70, 130, 180))  # Same color as video timeline

        start_x = 0
        for cut in sorted(self.cuts):
            cut_x = int(cut * self.pixel_per_second)
            self.drawSegment(painter, start_x, cut_x - 2)  # Add space between segments
            start_x = cut_x + 2  # Move start_x to next position with space

        self.drawSegment(painter, start_x, total_width)

        if self.audio_data is not None:
            painter.setBrush(QtGui.QColor(255, 255, 255))  # White color for waveform
            step = max(1, len(self.audio_data) // total_width)
            for x in range(total_width):
                value = abs(self.audio_data[x * step] * self.volume_scale) * self.height() // 2
                painter.drawRoundedRect(int(x), int(self.height() // 2 - value), 1, int(value * 2), 1, 1)

        if self.selected:
            painter.setBrush(QtGui.QColor(0, 0, 255, 128))
            painter.drawRoundedRect(0, 0, total_width, self.height(), 10, 10)

    def drawSegment(self, painter, start_x, end_x):
        width = end_x - start_x
        if width > 0:
            painter.drawRoundedRect(start_x, 0, width, self.height(), 10, 10)

    def generate_waveform(self, audio_path):
        def load_audio():
            try:
                # Extract audio from video
                video_clip = VideoFileClip(audio_path)
                audio_path_extracted = "extracted_audio.wav"
                video_clip.audio.write_audiofile(audio_path_extracted)
                self.file_name = os.path.basename(audio_path)  # Set file name
                # Load audio using librosa
                y, sr = librosa.load(audio_path_extracted, sr=None, mono=True)
                self.audio_data = y
                self.update()
            except Exception as e:
                print(f"Error generating waveform: {e}")

        threading.Thread(target=load_audio).start()

    def updatePixelPerSecond(self, pixel_per_second):
        self.pixel_per_second = pixel_per_second
        self.setMinimumWidth(int(self.duration * self.pixel_per_second))
        self.update()

    def removeLastCut(self):
        if self.cuts:
            self.cuts.pop()
            self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self._getCuttingMode():
            cut_position = event.pos().x() / self.pixel_per_second
            self.addCut(cut_position)
            self._getBottomHalfWidget().addCutToPair(self, cut_position)
        else:
            self.selected = not self.selected
            self.update()
            print("AudioWaveformWidget clicked at position:", event.pos())

    def mouseMoveEvent(self, event):
        if self._getCuttingMode():
            self._getBottomHalfWidget().handleMouseMove(event)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._getCuttingMode():
            self._getBottomHalfWidget().handleLeaveEvent(event)
        super().leaveEvent(event)

    def _getCuttingMode(self):
        parent = self.parent()
        while parent and not hasattr(parent, 'cuttingMode'):
            parent = parent.parent()
        return parent.cuttingMode if parent else False

    def _getBottomHalfWidget(self):
        parent = self.parent()
        while parent and not hasattr(parent, 'addCutToPair'):
            parent = parent.parent()
        return parent if parent else None


class BottomHalfWidget(QtWidgets.QWidget):
    def __init__(self, controlWidget, parent=None):
        super().__init__(parent)
        self.controlWidget = controlWidget
        self.setupUi()
        if self.controlWidget:
            self.controlWidget.fileOpened.connect(self.load_video)
            self.controlWidget.positionChanged.connect(self.updatePlayheadPosition)
            self.controlWidget.mediaPlayer.positionChanged.connect(self.updatePlayheadFromMediaPosition)
            self.controlWidget.mediaPlayer.stateChanged.connect(self.updatePlayheadState)
        self.cuttingMode = False
        self.overlayWidget = OverlayWidget(self)
        self.overlayWidget.raise_()  # Ensure the overlay widget is always on top
        self.video_audio_pairs = []
        self.selected_video_audio_pair = None
        self.undoStack = deque(maxlen=100)
        self.redoStack = deque(maxlen=100)

    def setupUi(self):
        self.layout = QtWidgets.QVBoxLayout(self)
        self.scrollArea = QtWidgets.QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.timelineLayout = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.timeRulerWidget = TimeRulerWidget(parent=self.scrollAreaWidgetContents)
        self.timelineLayout.addWidget(self.timeRulerWidget)
        self.videoLayout = QtWidgets.QVBoxLayout()
        self.audioLayout = QtWidgets.QVBoxLayout()
        self.timelineLayout.addLayout(self.videoLayout)
        self.timelineLayout.addLayout(self.audioLayout)
        self.playhead = Playhead(self.scrollAreaWidgetContents)
        self.playhead.setGeometry(0, 0, 2, self.scrollAreaWidgetContents.height())
        self.layout.addWidget(self.scrollArea)
        self.setLayout(self.layout)
        self.setMouseTracking(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.playhead.setFixedHeight(self.scrollAreaWidgetContents.height())
        self.overlayWidget.resize(self.size())

    def updatePlayheadPosition(self, percentage):
        max_width = self.scrollAreaWidgetContents.width()
        new_x = (max_width * percentage) // 100
        self.playhead.move(new_x, self.playhead.y())
        self.playhead.raise_()

    def load_video_duration(self, video_filename):
        cap = cv2.VideoCapture(video_filename)
        duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS))
        cap.release()
        return duration

    def load_video(self, video_filename):
        duration = self.load_video_duration(video_filename)
        video_timeline_widget = VideoTimelineWidget(self.scrollAreaWidgetContents, bottom_half_widget=self)
        video_timeline_widget.updateDuration(duration, os.path.basename(video_filename))
        audio_waveform_widget = AudioWaveformWidget(self.scrollAreaWidgetContents)
        audio_waveform_widget.duration = duration
        audio_waveform_widget.generate_waveform(video_filename)
        self.videoLayout.addWidget(video_timeline_widget, alignment=QtCore.Qt.AlignVCenter)
        self.audioLayout.addWidget(audio_waveform_widget, alignment=QtCore.Qt.AlignVCenter)
        video_audio_pair = VideoAudioPair(video_timeline_widget, audio_waveform_widget)
        self.video_audio_pairs.append(video_audio_pair)

    def updatePlayheadPixelPerSecond(self, pixel_per_second):
        self.playhead.updatePixelPerSecond(pixel_per_second)
        self.playhead.raise_()

    def updatePlayheadFromMediaPosition(self, position):
        self.playhead.updatePlayheadFromVideoPosition(position / 1000.0)
        self.playhead.raise_()

    def updatePlayheadState(self, state):
        if state == QMediaPlayer.PlayingState:
            self.playhead.timer.start(100)
        else:
            self.playhead.timer.stop()
        self.playhead.raise_()

    def activateCuttingMode(self):
        self.cuttingMode = True
        self.setCursor(QtGui.QCursor(QtGui.QPixmap("cut.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio)))
        self.scrollAreaWidgetContents.mouseMoveEvent = self.handleMouseMove
        self.scrollAreaWidgetContents.leaveEvent = self.handleLeaveEvent

    def deactivateCuttingMode(self):
        self.cuttingMode = False
        self.unsetCursor()
        self.scrollAreaWidgetContents.mouseMoveEvent = None
        self.scrollAreaWidgetContents.leaveEvent = None
        self.overlayWidget.clearVerticalLine()

    def handleMouseMove(self, event):
        if self.cuttingMode:
            self.overlayWidget.setVerticalLineX(event.pos().x())

    def handleLeaveEvent(self, event):
        self.overlayWidget.clearVerticalLine()

    def addCutToPair(self, widget, cut_position):
        for pair in self.video_audio_pairs:
            if pair.video_widget == widget or pair.audio_widget == widget:
                pair.video_widget.addCut(cut_position)
                pair.audio_widget.addCut(cut_position)
                self.addActionToUndoStack(cut_position)
                break

    def linkVideoAudioSelection(self, widget):
        for pair in self.video_audio_pairs:
            if pair.video_widget == widget or pair.audio_widget == widget:
                if pair.video_widget.selected:
                    pair.video_widget.selected = False
                    pair.audio_widget.selected = False
                    self.selected_video_audio_pair = None
                else:
                    pair.video_widget.selected = True
                    pair.audio_widget.selected = True
                    self.selected_video_audio_pair = pair
            else:
                pair.video_widget.selected = False
                pair.audio_widget.selected = False
            pair.video_widget.update()
            pair.audio_widget.update()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Backspace and self.selected_video_audio_pair:
            self.videoLayout.removeWidget(self.selected_video_audio_pair.video_widget)
            self.audioLayout.removeWidget(self.selected_video_audio_pair.audio_widget)
            self.selected_video_audio_pair.video_widget.setParent(None)
            self.selected_video_audio_pair.audio_widget.setParent(None)
            self.video_audio_pairs.remove(self.selected_video_audio_pair)
            self.selected_video_audio_pair = None
            self.update()
        elif event.key() == QtCore.Qt.Key_Z and event.modifiers() == QtCore.Qt.ControlModifier:
            self.undoLastAction()
        elif event.key() == QtCore.Qt.Key_Y and event.modifiers() == QtCore.Qt.ControlModifier:
            self.redoLastAction()

    def addActionToUndoStack(self, cut_position):
        self.undoStack.append(cut_position)
        self.redoStack.clear()

    def undoLastAction(self):
        if self.undoStack:
            last_action = self.undoStack.pop()
            for pair in self.video_audio_pairs:
                pair.video_widget.removeLastCut()
                pair.audio_widget.removeLastCut()
            self.redoStack.append(last_action)
            self.update()

    def redoLastAction(self):
        if self.redoStack:
            last_action = self.redoStack.pop()
            for pair in self.video_audio_pairs:
                pair.video_widget.addCut(last_action)
                pair.audio_widget.addCut(last_action)
            self.undoStack.append(last_action)
            self.update()

    def separateAudioVideo(self, widget):
        for pair in self.video_audio_pairs:
            if pair.video_widget == widget or pair.audio_widget == widget:
                self.video_audio_pairs.remove(pair)
                break
        self.update()

    def linkAudioVideo(self, widget):
        if isinstance(widget, AudioWaveformWidget):
            audio_widget = widget
            video_widget = None
            for pair in self.video_audio_pairs:
                if pair.audio_widget == audio_widget:
                    video_widget = pair.video_widget
                    break
            if video_widget:
                if audio_widget.file_name == video_widget.file_name:
                    self.video_audio_pairs.append(VideoAudioPair(video_widget, audio_widget))
                    print("Linked video and audio widgets.")
        elif isinstance(widget, VideoTimelineWidget):
            video_widget = widget
            audio_widget = None
            for pair in self.video_audio_pairs:
                if pair.video_widget == video_widget:
                    audio_widget = pair.audio_widget
                    break
            if audio_widget:
                if video_widget.file_name == audio_widget.file_name:
                    self.video_audio_pairs.append(VideoAudioPair(video_widget, audio_widget))
                    print("Linked video and audio widgets.")


class TopHalfWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()

    def setupUi(self):
        mainLayout = QtWidgets.QHBoxLayout(self)
        self.transcribeText = QtWidgets.QTextEdit(self)
        self.transcribeText.setPlaceholderText("Transcription will appear here...")
        self.transcribeText.setReadOnly(True)
        self.transcribeText.setMinimumWidth(200)

        self.videoWidget = QVideoWidget(self)
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.videoWidget.setMinimumSize(600, 400)

        self.aiToolsStack = QtWidgets.QStackedWidget(self)
        self.aiToolsStack.addWidget(QtWidgets.QLabel("Basic Enhancements Page", self))
        self.aiToolsStack.addWidget(QtWidgets.QLabel("Advanced Editing Tools Page", self))
        self.aiToolsStack.addWidget(QtWidgets.QLabel("AI Features Page", self))
        self.aiToolsStack.setMinimumWidth(200)

        navigationLayout = QtWidgets.QVBoxLayout()
        self.navigationButtons = []
        for i in range(3):
            button = QtWidgets.QPushButton(f"Page {i + 1}", self)
            button.clicked.connect(lambda checked, index=i: self.aiToolsStack.setCurrentIndex(index))
            self.navigationButtons.append(button)
            navigationLayout.addWidget(button)

        mainLayout.addWidget(self.transcribeText)
        mainLayout.addWidget(self.videoWidget)
        mainLayout.addWidget(self.aiToolsStack)
        mainLayout.addLayout(navigationLayout)

        self.setLayout(mainLayout)

    def toggle_playback(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()
        self.update_playback_icon()

    def update_playback_icon(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playPauseButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
        else:
            self.playPauseButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))

    def duration_changed(self, duration):
        self.positionSlider.setRange(0, duration)

    def position_changed(self, position):
        if not self.positionSlider.isSliderDown():
            self.positionSlider.setValue(position)


class ControlWidget(QtWidgets.QWidget):
    sliderMoved = QtCore.pyqtSignal(int)
    positionChanged = QtCore.pyqtSignal(int)
    fileOpened = QtCore.pyqtSignal(str)

    def __init__(self, mediaPlayer, parent=None):
        super().__init__(parent)
        self.mediaPlayer = mediaPlayer
        self.setupUi()

    def setupUi(self):
        layout = QtWidgets.QHBoxLayout(self)

        # Open File Button
        self.openFileButton = QtWidgets.QPushButton("Open File", self)
        self.openFileButton.clicked.connect(self.openFile)
        self.openFileButton.setToolTip("Open a video file")
        layout.addWidget(self.openFileButton)

        # Duration Label
        self.durationLabel = QtWidgets.QLabel("00:00:00 / 00:00:00", self)
        layout.addWidget(self.durationLabel)

        # Play/Pause Button
        self.playPauseButton = QtWidgets.QPushButton(self)
        self.playPauseButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
        self.playPauseButton.clicked.connect(self.togglePlayback)
        self.playPauseButton.setToolTip("Play/Pause the video")
        layout.addWidget(self.playPauseButton)

        # Position Slider
        self.positionSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.positionSlider.sliderMoved.connect(self.setPosition)
        self.mediaPlayer.durationChanged.connect(self.duration_changed)
        self.mediaPlayer.positionChanged.connect(self.position_changed)
        self.mediaPlayer.positionChanged.connect(self.handlePositionChanged)
        self.positionSlider.sliderMoved.connect(self.handleSliderMoved)
        layout.addWidget(self.positionSlider)

        self.setLayout(layout)

    def handlePositionChanged(self, position):
        totalDuration = self.mediaPlayer.duration() if self.mediaPlayer.duration() > 0 else 1
        percentage = int((position / totalDuration) * 100)
        self.positionChanged.emit(percentage)
        if not self.positionSlider.isSliderDown():
            self.positionSlider.setValue(position)
        self.updateDurationLabel()

    def openFile(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Video", "",
                                                            "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if fileName:
            self.mediaPlayer.setMedia(QMediaContent(QtCore.QUrl.fromLocalFile(fileName)))
            self.mediaPlayer.pause()
            self.fileOpened.emit(fileName)

    def setPosition(self, position):
        if position != self.mediaPlayer.position():
            self.mediaPlayer.setPosition(position)

    def duration_changed(self, duration):
        self.positionSlider.setRange(0, duration)
        self.updateDurationLabel()

    def position_changed(self, position):
        if not self.positionSlider.isSliderDown():
            self.positionSlider.setValue(position)
        self.updateDurationLabel()

    def handleSliderMoved(self, position):
        self.setPosition(position)
        totalDuration = self.mediaPlayer.duration() if self.mediaPlayer.duration() > 0 else 1
        percentage = int((position / totalDuration) * 100)
        self.sliderMoved.emit(percentage)
        self.updateDurationLabel()

    def togglePlayback(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()
        self.updatePlaybackIcon()

    def updatePlaybackIcon(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playPauseButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
        else:
            self.playPauseButton.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))

    def updateDurationLabel(self):
        position = self.mediaPlayer.position() // 1000
        duration = self.mediaPlayer.duration() // 1000
        self.durationLabel.setText(f"{self.formatTime(position)} / {self.formatTime(duration)}")

    def formatTime(self, seconds):
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"


class TimeRulerWidget(QtWidgets.QWidget):
    zoomLevelChanged = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoomLevel = 1
        self.duration = 4 * 3600  # Fixed duration of 4 hours in seconds
        self.setMinimumHeight(50)
        self.pixel_per_second = 10

        self.setZoomLevels()
        self.setupZoomSlider()
        self.updateWidth()
        self.setupButtons()

    def setupZoomSlider(self):
        self.zoomSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.zoomSlider.setGeometry(10, 35, 150, 15)
        self.zoomSlider.setMinimum(1)
        self.zoomSlider.setMaximum(6)
        self.zoomSlider.setValue(1)
        self.zoomSlider.setTickInterval(1)
        self.zoomSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.zoomSlider.valueChanged.connect(self.setZoomLevel)

    def setupButtons(self):
        self.cutButton = QtWidgets.QPushButton(self)
        self.cutButton.setIcon(QtGui.QIcon("cut.png"))
        self.cutButton.setGeometry(170, 35, 30, 30)
        self.cutButton.clicked.connect(self.activateCuttingMode)
        self.cutButton.setStyleSheet("QPushButton { background-color: #FF5733; border-radius: 5px; }")
        self.cutButton.setToolTip("Activate Cutting Mode")

        self.cursorButton = QtWidgets.QPushButton(self)
        self.cursorButton.setIcon(QtGui.QIcon("cursor.png"))
        self.cursorButton.setGeometry(210, 35, 30, 30)
        self.cursorButton.clicked.connect(self.deactivateCuttingMode)
        self.cursorButton.setStyleSheet("QPushButton { background-color: #FF5733; border-radius: 5px; }")
        self.cursorButton.setToolTip("Deactivate Cutting Mode")

    def setZoomLevel(self, zoom):
        if zoom != self.zoomLevel:
            self.zoomLevel = zoom
            self.zoomLevelChanged.emit(zoom)
            self.updateWidth()
            self.update()

    def setZoomLevels(self):
        self.zoomSettings = {
            1: 1800,  # Label every 30 minutes
            2: 600,   # Label every 10 minutes
            3: 300,   # Label every 5 minutes
            4: 60,    # Label every 1 minute
            5: 30,    # Label every 30 seconds
            6: 10     # Label every 10 seconds
        }
        self.minorTickSettings = {
            1: 300,   # Minor tick every 5 minutes
            2: 60,    # Minor tick every 1 minute
            3: 30,    # Minor tick every 30 seconds
            4: 10,    # Minor tick every 10 seconds
            5: 5,     # Minor tick every 5 seconds
            6: 1      # Minor tick every second
        }

    def updateWidth(self):
        base_pixels_per_second = [0.1, 0.2, 1, 5, 10, 20]
        self.pixel_per_second = base_pixels_per_second[self.zoomLevel - 1]
        total_pixels = int(self.duration * self.pixel_per_second)
        self.setMinimumWidth(total_pixels)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QColor(80, 80, 80))

        major_interval = self.zoomSettings[self.zoomLevel]
        minor_interval = self.minorTickSettings[self.zoomLevel]

        for i in range(0, self.duration + 1, minor_interval):
            x = int(i * self.pixel_per_second)
            painter.drawLine(x, 0, x, 10)

        for i in range(0, self.duration + 1, major_interval):
            x = int(i * self.pixel_per_second)
            painter.drawLine(x, 0, x, 20)
            if i % major_interval == 0:
                seconds = i
                hours, remainder = divmod(seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                if self.zoomLevel > 4:
                    label = f"{hours}h {minutes:02}m {seconds}s" if hours else f"{minutes}m {seconds}s"
                else:
                    label = f"{hours}h {minutes:02}m" if hours else f"{minutes}m"
                painter.drawText(x + 5, 30, label)

    def activateCuttingMode(self):
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtGui.QPixmap("cut.png").scaled(16, 16, QtCore.Qt.KeepAspectRatio)))  # Make the cutting icon smaller
        parent = self.parent()
        while parent and not hasattr(parent, 'activateCuttingMode'):
            parent = parent.parent()
        if parent:
            parent.activateCuttingMode()

    def deactivateCuttingMode(self):
        QtWidgets.QApplication.restoreOverrideCursor()
        parent = self.parent()
        while parent and not hasattr(parent, 'deactivateCuttingMode'):
            parent = parent.parent()
        if parent:
            parent.deactivateCuttingMode()


class VideoAudioPair:
    def __init__(self, video_widget, audio_widget):
        self.video_widget = video_widget
        self.audio_widget = audio_widget


class OverlayWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalLineX = None
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.line_length_factor = 1  # Full-length line

    def setVerticalLineX(self, x):
        self.verticalLineX = x
        self.update()

    def clearVerticalLine(self):
        self.verticalLineX = None
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.verticalLineX is not None:
            painter = QtGui.QPainter(self)
            painter.setPen(QtGui.QColor(0, 0, 0))
            line_length = int(self.height() * self.line_length_factor)
            painter.drawLine(self.verticalLineX, 0, self.verticalLineX, line_length)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.topHalfWidget = TopHalfWidget()
        self.controlWidget = ControlWidget(self.topHalfWidget.mediaPlayer)
        self.bottomHalfWidget = BottomHalfWidget(controlWidget=self.controlWidget)

        self.timerulerWidget = self.bottomHalfWidget.timeRulerWidget
        self.timerulerWidget.zoomLevelChanged.connect(self.updatePixelPerSecond)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(self.topHalfWidget)
        mainLayout.addWidget(self.controlWidget)
        mainLayout.addWidget(self.bottomHalfWidget)

        mainWidget = QtWidgets.QWidget()
        mainWidget.setLayout(mainLayout)
        self.setCentralWidget(mainWidget)

        self.setWindowTitle('Video Editor')
        self.resize(1920, 1080)
        self.center()

        self.setupShortcuts()

    def center(self):
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2,
                  (screen.height() - size.height()) // 2)

    def closeEvent(self, event):
        super().closeEvent(event)

    def updatePixelPerSecond(self, zoomLevel):
        base_pixels_per_second = [0.1, 0.2, 1, 5, 10, 20]
        pixel_per_second = base_pixels_per_second[zoomLevel - 1]
        for pair in self.bottomHalfWidget.video_audio_pairs:
            pair.video_widget.updatePixelPerSecond(pixel_per_second)
            pair.audio_widget.updatePixelPerSecond(pixel_per_second)
        self.bottomHalfWidget.updatePlayheadPixelPerSecond(pixel_per_second)

    def setupShortcuts(self):
        undoShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self)
        undoShortcut.activated.connect(self.bottomHalfWidget.undoLastAction)

        redoShortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Y"), self)
        redoShortcut.activated.connect(self.bottomHalfWidget.redoLastAction)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
