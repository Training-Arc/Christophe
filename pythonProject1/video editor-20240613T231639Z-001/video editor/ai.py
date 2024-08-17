from openai import OpenAI
from moviepy.editor import VideoFileClip
import os
import tempfile
client = OpenAI()

content_prompt = """You are an advanced text refinement tool designed to process video transcripts efficiently. Your primary function is to improve the readability and conciseness of transcripts by automatically removing filler words ("um", "uh", "you know", etc.), unnecessary repetitions, long pauses indicated by ellipses or repeated punctuation marks, and correcting or removing bad takes such as sentences that start but do not finish properly.

Your task is to process a given transcript and return a refined version of it. The refined transcript should:
- Exclude filler words and phrases that do not contribute meaningful content.
- Remove redundant sentences or phrases that repeat the same information without adding value.
- Clean up segments with long pauses, which might be represented by multiple ellipses (...) or dashes (-).
- Edit or omit bad takes, including incomplete thoughts or sentences that derail from the main topic.

The output should retain the original message and information of the transcript but in a more polished, concise form. The structure and flow of the content should remain intact, ensuring that the essence of the speaker's points is preserved without the unnecessary fluff.

Please perform this cleanup operation directly on the following transcript:
"""

def extract_and_transcribe_audio(file_path):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmpfile:
        temp_audio_path = tmpfile.name

    if file_path.endswith(('.mp4', '.mov', '.avi')):
        video = VideoFileClip(file_path)
        video.audio.write_audiofile(temp_audio_path)
        video.close()
    else:
        temp_audio_path = file_path

    with open(temp_audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )

    if file_path.endswith(('.mp4', '.mov', '.avi')):
        os.remove(temp_audio_path)

    return transcription.text


def get_editing_suggestions(transcript):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": content_prompt
            },
            {
                "role": "user",
                "content": transcript
            }
        ],
        temperature=0.8,
        max_tokens=200,
        top_p=1
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    file_path = "C1193 - L - Systems and Websites_1.mp4"
    transcript = extract_and_transcribe_audio(file_path)
    editing_suggestions = get_editing_suggestions(transcript)
    print(editing_suggestions)
