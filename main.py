# Make sure to install moviepy: pip install moviepy
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip
import numpy as np  # Often needed for color clip dimensions


def convert_text_format(text: str):
    """
    Converts text into a different format using a LLaMA-like language model from Hugging Face.
    Returns the model's response string.

    NOTE: This is an illustrative function. You should replace the model path and
          adapt prompt instructions to suit your actual use case.
    """
    with open('subs.ass', 'r', encoding='utf-8') as file:
        subtitle_text = file.read()
        prompt_text = f"Convert this {subtitle_text} into this format: {text}. IT IS IMPORTANT THAT YOU DO NOT ADD ANY EXTRA TEXT. ONLY RETURN THE FORMATTED TEXT."
        from llama_cpp import Llama
        from replit.object_storage import Client
        client = Client()

        llm = Llama(
              model_path="llama-model.gguf",
              # n_gpu_layers=-1, # Uncomment to use GPU acceleration
              # seed=1337, # Uncomment to set a specific seed
              # n_ctx=2048, # Uncomment to increase the context window
        )
        output = llm(
            prompt_text, # Prompt
              max_tokens=3200, # Generate up to 32 tokens, set to None to generate up to the end of the context window
              stop=["Q:", "\n"], # Stop generating just before the model would generate a new question
              echo=True # Echo the prompt back in the output
        ) # Generate a completion, can also call create_completion
        print(output)
        return output


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


# --- Example Usage ---
texts = [{
    'text': 'This is the first test subtitle line.',
    'start': 2,
    'end': 5.5,
    'pos': 'center',
    'fontsize': 48,
    'color': 'blue'
}, {
    'text': 'Here is a second subtitle entry.\nIt contains two lines.',
    'start': 6.1,
    'end': 9.8,
    'pos': 'center',
    'fontsize': 48,
    'color': 'green'
}, {
    'text': 'This is the third and final test line.',
    'start': 10,
    'end': 13.25,
    'pos': 'center',
    'fontsize': 48,
    'color': 'magenta'
}]

print(str(convert_text_format(str(texts))))

# Make sure 'input.mp4' exists
add_text_box('input.mp4', 'output_with_text.mp4',
             str(convert_text_format(str(texts))))
print("Video processing complete.")
