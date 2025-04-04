# Make sure to install moviepy: pip install moviepy
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip
import numpy as np  # Often needed for color clip dimensions

import re


def parse_ass_to_dicts_first_color(ass_text):
    """
    Parse an ASS subtitle script and return a list of dictionaries like:
      [
        {
          'text': 'This is the first test subtitle line.',
          'start': 2.0,
          'end': 5.5,
          'pos': 'center',
          'fontsize': 48,
          'color': 'blue'
        },
        ...
      ]
    We take the *first* color code we find in each line and map it to a color name.
    """

    # Simple mapping from 6-digit RGB hex to color names you want.
    # If you need more codes, just add them here:
    color_map = {
        '0000FF': 'blue',
        '00FF00': 'green',
        'FF0000': 'red',
        'FFFF00': 'yellow',
        'FF00FF': 'magenta',
        'FFFFFF': 'white',
        '000000': 'black'
    }

    # Regex to find color codes in text: e.g. {\1c&HFF00FF&}
    color_tag_pattern = re.compile(r'\{\\1c&H([0-9A-Fa-f]{6})&\}')

    # We will store found default font size from `[V4+ Styles]` if possible
    default_fontsize = 48  # fallback if not found

    texts = []

    lines = ass_text.splitlines()
    in_styles_section = False
    in_events_section = False

    for line in lines:
        line_stripped = line.strip()

        # Detect section starts
        if line_stripped.startswith('[V4+ Styles]'):
            in_styles_section = True
            in_events_section = False
            continue
        elif line_stripped.startswith('[Events]'):
            in_styles_section = False
            in_events_section = True
            continue

        # --- Parse style line to find default font size ---
        if in_styles_section and line_stripped.startswith('Style:'):
            # Something like:
            #  Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,...
            parts = line_stripped.split(',')
            # parts[0] = "Style: Default"
            # parts[1] = "Arial"
            # parts[2] = "48" <-- usually the font size
            style_name = parts[0].split(':', 1)[1].strip()  # "Default"
            if style_name.lower() == 'default':
                try:
                    default_fontsize = int(parts[2])
                except:
                    pass

        # --- Parse "Dialogue:" lines in [Events] section ---
        if in_events_section and line_stripped.startswith('Dialogue:'):
            # The standard format after "Dialogue:" is comma-delimited:
            #  Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
            # We'll do a split with a maxsplit=9 so we don't break the text if it contains commas
            fields = line_stripped.split(',', 9)
            if len(fields) < 10:
                # Not well-formed, skip
                continue

            # fields[1] = Start e.g. 0:00:02.00
            # fields[2] = End   e.g. 0:00:05.50
            # fields[9] = "Text"

            start_str = fields[1].strip()
            end_str = fields[2].strip()
            text_raw = fields[9].strip()

            # Convert start, end times (h:mm:ss.xx) to float seconds if you like:
            start_seconds = _ass_time_to_seconds(start_str)
            end_seconds = _ass_time_to_seconds(end_str)

            # Find the *first* color code if it exists
            found_colors = color_tag_pattern.findall(text_raw)
            chosen_color = None
            if found_colors:
                first_code = found_colors[0].upper()  # e.g. "0000FF"
                chosen_color = color_map.get(
                    first_code, 'white')  # default if not recognized
            else:
                chosen_color = 'white'

            # Remove all color tags from the text
            text_clean = color_tag_pattern.sub('', text_raw)

            # Also remove empty {\1c}, if present (to revert color) – for cleanliness
            text_clean = re.sub(r'\{\\1c\}', '', text_clean)

            # Replace \N with actual newlines
            text_clean = text_clean.replace(r'\N', '\n')

            # For the sake of the example, let's assume position is always center
            # because the style alignment was "2" for center in your example.
            pos = 'center'

            # Build the dictionary
            item = {
                'text': text_clean,
                'start': start_seconds,
                'end': end_seconds,
                'pos': pos,
                'fontsize': default_fontsize,
                'color': chosen_color
            }
            texts.append(item)
    print(texts)
    return texts


def _ass_time_to_seconds(timestr):
    """
    Convert an ASS time string like '0:00:06.10' into float seconds (6.1).
    """
    # Usually in format H:MM:SS.xx or HH:MM:SS.xx
    # e.g. "0:00:06.10"
    h, m, s = timestr.split(':')
    hours = int(h)
    minutes = int(m)
    seconds = float(s)
    return hours * 3600 + minutes * 60 + seconds


def add_text_box(
    input_video_path,
    output_video_path,
    text_info_list  # List of dictionaries
    # Each dict: {'text': 'My Text', 'start': 10, 'end': 15, 'pos': ('center', 'bottom'),
    #             'fontsize': 24, 'color': 'white', 'bg_color': 'black', 'bg_opacity': 0.5}
):
    """
    Adds multiple text boxes to a video at specified times.

    Args:
        input_video_path (str): Path to the input video file.
        output_video_path (str): Path to save the output video file.
        text_info_list (list): A list of dictionaries, each defining a text box.
                                Keys: 'text', 'start', 'end', 'pos', 'fontsize',
                                      'color', 'bg_color', 'bg_opacity'.
                                      'pos' can be tuple (x,y) or ('center', 'top'), etc.
                                      'bg_opacity' ranges from 0 (transparent) to 1 (opaque).
    """

    
    video_clip = VideoFileClip(input_video_path)
    clips_to_composite = [video_clip]  # Start with the base video

    for info in text_info_list:
        # if it has synonyms or antonyms, add the text box
        # Create the text clip
        txt_clip = TextClip(
            text=info['text'],
            color=info.get('color', 'white'),
            # Optional: Specify font, stroke_color, stroke_width etc.
            font='VeganStylePersonalUse-5Y58.ttf',
            font_size=info.get('fontsize', 24),
            # method='caption', # Use 'caption' for auto-wrapping if needed
            # size=(video_clip.w * 0.8, None) # Example: max width 80% of video
        )

        # Create background clip (optional, for a distinct box)
        if 'bg_color' in info:
            # Add padding around the text
            padding = 10
            txt_width, txt_height = txt_clip.size
            bg_width = txt_width + 2 * padding
            bg_height = txt_height + 2 * padding

            # Use ColorClip for solid background
            bg_clip = ColorClip(
                size=(bg_width, bg_height),
                color=(255, 255, 255)  # Requires numpy
            )
            if 'bg_opacity' in info:
                bg_clip = bg_clip.with_opacity(info['bg_opacity'])

            # Composite text onto the background, centering text within the padded box
            txt_on_bg_clip = CompositeVideoClip(
                [bg_clip, txt_clip.with_position('center')],
                size=(bg_width, bg_height
                      )  # Ensure composite clip has the bg size
            )
            final_text_element = txt_on_bg_clip
        else:
            # Just use the text clip directly if no background is needed
            final_text_element = txt_clip

        # Set position, start time, and duration/end time
        final_text_element = final_text_element.with_position(
            info.get('pos', 'center'))
        final_text_element = final_text_element.with_start(info['start'])
        final_text_element = final_text_element.with_end(info['end'])
        # Or use duration: .set_duration(info['end'] - info['start'])

        clips_to_composite.append(final_text_element)

    # Composite all text clips onto the main video
    final_clip = CompositeVideoClip(clips_to_composite)

    # Write the result to a file
    # Use appropriate codec, bitrate, etc., as needed
    final_clip.write_videofile(output_video_path,
                               codec='libx264',
                               audio_codec='aac')

    # Close clips to release resources
    video_clip.close()
    for clip in clips_to_composite[1:]:  # Skip the original video clip
        if hasattr(clip, 'close'):
            clip.close()
    final_clip.close()


with open('subs.ass', 'r') as f:
    ass_text = f.read()
    # Make sure 'input.mp4' exists
    add_text_box('input.mp4', 'output_with_text.mp4',
                 parse_ass_to_dicts_first_color(ass_text))
    print("Video processing complete.")
