import QtQuick 2.15
import QtQuick.Controls 2.15
import QtMultimedia 5.15

ApplicationWindow {
    visible: true
    width: 1920
    height: 1080
    title: "Video Editor"

    header: ToolBar {
        contentHeight: 40
        RowLayout {
            spacing: 10
            ToolButton {
                text: "Open File"
                onClicked: fileDialog.open()
            }
            FileDialog {
                id: fileDialog
                nameFilters: ["Video Files (*.mp4 *.avi *.mkv *.mov)"]
                onAccepted: {
                    if (fileDialog.fileUrl) {
                        backend.openFile(fileDialog.fileUrl.toLocalFile())
                    } else {
                        console.log("Error: Invalid file selected")
                    }
                }
                onRejected: {
                    console.log("File selection cancelled")
                }
            }
        }
    }

    VideoOutput {
        id: videoOutput
        anchors.fill: parent
        source: mediaPlayer
        fillMode: VideoOutput.PreserveAspectFit
    }

    MediaPlayer {
        id: mediaPlayer
    }

    Rectangle {
        id: timeline
        width: parent.width
        height: 60
        color: "#444"
        anchors.bottom: parent.bottom

        // Example timeline
        Repeater {
            model: 10
            Rectangle {
                width: 100
                height: 60
                color: index % 2 === 0 ? "#666" : "#888"
                border.color: "#000"
                Text {
                    anchors.centerIn: parent
                    text: index + 1
                    color: "#FFF"
                }
            }
        }
    }

    Button {
        text: mediaPlayer.playbackState === MediaPlayer.PlayingState ? "Pause" : "Play"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: timeline.top
        onClicked: {
            if (mediaPlayer.playbackState === MediaPlayer.PlayingState) {
                mediaPlayer.pause()
            } else {
                mediaPlayer.play()
            }
        }
    }

    Connections {
        target: mediaPlayer
        onError: {
            console.log("Error occurred in media player: " + errorString)
        }
    }
}
