import whisper
import moviepy.editor as mp
import datetime
import os
import argparse
import sys
import json  # Added for JSON output


def format_timestamp(seconds):
    """Converts seconds (float) to SRT timestamp format HH:MM:SS,ms"""
    delta = datetime.timedelta(seconds=seconds)
    total_seconds = int(delta.total_seconds())
    microseconds = delta.microseconds
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = microseconds // 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def create_subtitles(video_path,
                     model_name="base",
                     output_srt=None,
                     output_json=None,
                     word_level=True):
    """
    Extracts audio, transcribes (optionally with word timings),
    and creates SRT and/or JSON subtitle files.

    Args:
        video_path (str): Path to the input MP4 video file.
        model_name (str): Whisper model name ("tiny", "base", "small", "medium", "large").
        output_srt (str, optional): Path for the output SRT file. Defaults to video filename + .srt.
        output_json (str, optional): Path for the output JSON file (for word timings). Defaults to video filename + .json.
        word_level (bool): Whether to request and save word-level timestamps (in JSON).
    """
    print(f"Starting subtitle generation for: {video_path}")
    print(f"Using Whisper model: {model_name}")
    print(f"Word-level timestamps requested: {word_level}")

    # --- 1. Input Validation & Path Setup ---
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        sys.exit(1)

    base_filename = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = os.path.dirname(
        video_path) or "."  # Use current dir if no path provided

    if output_srt is None:
        output_srt = os.path.join(output_dir, f"{base_filename}.srt")
    if output_json is None and word_level:
        output_json = os.path.join(output_dir,
                                   f"{base_filename}_word_timestamps.json")

    # Use a more robust temporary file naming scheme
    pid = os.getpid()
    temp_audio_path = os.path.join(output_dir,
                                   f"temp_audio_{base_filename}_{pid}.mp3")

    video = None
    try:
        # --- 2. Audio Extraction ---
        print("Extracting audio...")
        video = mp.VideoFileClip(video_path)
        if video.audio is None:
            print(
                f"Error: The video file {video_path} does not contain an audio track."
            )
            if video: video.close()  # Close if opened
            sys.exit(1)

        video.audio.write_audiofile(temp_audio_path, codec='mp3')
        print(f"Audio extracted to: {temp_audio_path}")
        video.close()
        video = None

        # --- 3. Transcription ---
        print("Loading Whisper model...")
        model = whisper.load_model(model_name)
        print(
            "Model loaded. Starting transcription (this may take a while)...")

        # Request word timestamps if needed
        result = model.transcribe(temp_audio_path,
                                  word_timestamps=word_level,
                                  fp16=False)
        print("Transcription complete.")

        # --- 4. SRT File Generation (Segment Level) ---
        print(f"Generating SRT file: {output_srt}")
        with open(output_srt, "w", encoding="utf-8") as srt_file:
            for i, segment in enumerate(result['segments']):
                start_time = format_timestamp(segment['start'])
                end_time = format_timestamp(segment['end'])
                text = segment['text'].strip()
                srt_file.write(f"{i + 1}\n")
                srt_file.write(f"{start_time} --> {end_time}\n")
                srt_file.write(f"{text}\n\n")
        print(f"SRT file saved to: {output_srt}")

        # --- 5. JSON File Generation (Word Level, if requested) ---
        if word_level:
            if not output_json:  # Should have been set above, but double check
                output_json = os.path.join(
                    output_dir, f"{base_filename}_word_timestamps.json")
            print(f"Generating JSON file with word timestamps: {output_json}")

            # Structure the JSON data clearly
            output_data = {
                "metadata": {
                    "video_file": video_path,
                    "model_used": model_name,
                    "transcription_time": datetime.datetime.now().isoformat(),
                    "whisper_detected_language": result.get("language", "N/A")
                },
                "segments": []
            }

            # Check if word timestamps are actually present in the result
            if result['segments'] and 'words' in result['segments'][0]:
                for segment in result['segments']:
                    segment_data = {
                        "segment_id": segment['id'],
                        "start": segment['start'],
                        "end": segment['end'],
                        "text": segment['text'].strip(),
                        "words": []
                    }
                    for word_info in segment.get(
                            'words', []):  # Iterate through words in segment
                        segment_data["words"].append({
                            "word":
                            word_info['word'].strip(),
                            # Use .get for robustness in case a key is missing
                            "start":
                            word_info.get('start'),
                            "end":
                            word_info.get('end'),
                            "probability":
                            word_info.get('probability')
                        })
                    output_data["segments"].append(segment_data)

                with open(output_json, "w", encoding="utf-8") as json_file:
                    json.dump(output_data,
                              json_file,
                              indent=4,
                              ensure_ascii=False)  # Use indent for readability
                print(f"JSON file saved to: {output_json}")
            else:
                print(
                    "Warning: Word timestamps requested, but not found in Whisper result. Skipping JSON generation."
                )
                # Optionally delete the intended JSON path if it existed somehow
                if os.path.exists(output_json): os.remove(output_json)

        print("-" * 30)
        print(f"Processing complete for {base_filename}")
        print("-" * 30)

    except Exception as e:
        print(f"\n--- An error occurred during processing ---")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        # Uncomment for full traceback
        # import traceback
        # traceback.print_exc()
        print("------------------------------------------")
        if video:
            try:
                video.close()
            except Exception as close_err:
                print(f"Error closing video file during cleanup: {close_err}")

    finally:
        # --- 6. Cleanup ---
        if os.path.exists(temp_audio_path):
            print(f"Cleaning up temporary audio file: {temp_audio_path}")
            try:
                os.remove(temp_audio_path)
            except Exception as del_err:
                print(
                    f"Warning: Error deleting temporary file {temp_audio_path}: {del_err}"
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
        "Generate subtitles (SRT and optional JSON with word timings) for a video file."
    )
    parser.add_argument("video_path", help="Path to the input MP4 video file.")
    parser.add_argument(
        "-m",
        "--model",
        default="base",
        choices=[
            "tiny", "tiny.en", "base", "base.en", "small", "small.en",
            "medium", "medium.en", "large-v1", "large-v2", "large-v3", "large"
        ],
        help=
        "Whisper model size (default: base). '.en' models are English-only.")
    parser.add_argument(
        "-os",
        "--output_srt",
        default=None,
        help="Path for the output SRT file (default: <video_name>.srt).")
    parser.add_argument(
        "-oj",
        "--output_json",
        default=None,
        help=
        "Path for the output JSON file with word timings (default: <video_name>_word_timestamps.json). Only generated if --word_level is enabled."
    )
    parser.add_argument(
        "--no_word_level",
        action="store_false",
        dest="word_level",
        help=
        "Disable generation of word-level timestamps and the JSON output file."
    )
    parser.add_argument(
        "--word_level",
        action="store_true",
        dest="word_level",
        default=True,
        help=
        "Enable generation of word-level timestamps and the JSON output file (default)."
    )  # Explicit enable flag

    args = parser.parse_args()

    # Ensure JSON output path makes sense if word level is disabled
    json_output_path = args.output_json
    if not args.word_level:
        json_output_path = None  # Don't pass a JSON path if word level is off

    create_subtitles(args.video_path, args.model, args.output_srt,
                     json_output_path, args.word_level)
