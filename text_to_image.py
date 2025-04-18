#!/usr/bin/env python
import argparse
import os
from PIL import Image, ImageDraw, ImageFont

def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate an image with black text on white background')
    parser.add_argument('text', type=str, help='Text to render in the image')
    parser.add_argument('-f', '--font-size', type=int, default=24,
                        help='Font size to use (default: 24)')
    parser.add_argument('-o', '--output', type=str, default='text.png',
                        help='Output filename (default: text.png)')
    parser.add_argument('-w', '--width', type=int, default=384,
                        help='Image width in pixels (default: 384)')
    parser.add_argument('-p', '--padding', type=int, default=20,
                        help='Padding around text in pixels (default: 20)')
    return parser.parse_args()

def text_to_image(text, font_size=24, width=384, padding=20, output_file='text.png'):
    """
    Creates an image with black text on white background
    
    Args:
        text: The text to render
        font_size: Font size to use
        width: Width of the image in pixels
        padding: Padding around text in pixels
        output_file: Path to save the output image
    
    Returns:
        Path to the created image file
    """
    # Create a temporary image to measure text dimensions
    font_path = None
    
    # Try to find a font on the system
    font_options = [
        # Common font paths on macOS/Linux/Windows
        '/System/Library/Fonts/Helvetica.ttc',
        '/System/Library/Fonts/SFNSText.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/TTF/DejaVuSans.ttf',
        'C:\\Windows\\Fonts\\arial.ttf'
    ]
    
    for path in font_options:
        if os.path.exists(path):
            font_path = path
            break
    
    if font_path is None:
        # Use a default font if none of the above exist
        font = ImageFont.load_default()
    else:
        font = ImageFont.truetype(font_path, font_size)
    
    # Split text into lines to handle wrapping
    # First split by explicit newlines in the text
    paragraphs = text.split('\n')
    lines = []
    
    temp_img = Image.new('RGB', (1, 1), color='white')
    temp_draw = ImageDraw.Draw(temp_img)
    
    # Process each paragraph
    for paragraph in paragraphs:
        words = paragraph.split()
        current_line = []
        
        # If paragraph is empty, add an empty line
        if not words:
            lines.append("")
            continue
            
        for word in words:
            test_line = ' '.join(current_line + [word])
            line_width = temp_draw.textlength(test_line, font=font)
            
            if line_width <= (width - (padding * 2)):
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long for the line, but we'll add it anyway
                    # and it will get cut off or wrapped
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
    
    # Calculate height based on number of lines and font size
    line_height = font_size + 4  # Add a little extra space between lines
    height = (len(lines) * line_height) + (padding * 2)
    
    # Create the actual image
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw text line by line
    y_pos = padding
    for line in lines:
        draw.text((padding, y_pos), line, font=font, fill='black')
        y_pos += line_height
    
    # Save the image
    img.save(output_file)
    
    return output_file

def main():
    args = parse_args()
    
    # Replace literal '\n' with actual newlines
    text = args.text.replace('\\n', '\n')
    
    output_file = text_to_image(
        text,
        font_size=args.font_size,
        width=args.width,
        padding=args.padding,
        output_file=args.output
    )
    
    print(f"Image created: {output_file}")
    
    # Display the image (uncomment if desired)
    # img = cv2.imread(output_file)
    # cv2.imshow('Text Image', img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

if __name__ == '__main__':
    main() 