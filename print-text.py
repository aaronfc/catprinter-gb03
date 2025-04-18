#!/usr/bin/env python
import argparse
import sys
import os
import subprocess
import tempfile

def parse_args():
    parser = argparse.ArgumentParser(
        description='Creates an image from text and sends it to the cat printer')
    parser.add_argument('text', nargs='?', type=str, 
                        help='Text to print. If not provided, reads from stdin')
    parser.add_argument('-f', '--font-size', type=int, default=24,
                        help='Font size to use (default: 24)')
    parser.add_argument('-w', '--width', type=int, default=384,
                        help='Image width in pixels (default: 384)')
    parser.add_argument('-p', '--padding', type=int, default=20,
                        help='Padding around text in pixels (default: 20)')
    parser.add_argument('-b', '--img-binarization-algo', type=str,
                        choices=['mean-threshold', 'floyd-steinberg', 'atkinson', 'halftone', 'none'],
                        default='floyd-steinberg',
                        help='Which image binarization algorithm to use')
    parser.add_argument('-s', '--show-preview', action='store_true',
                        help='If set, displays the final image and asks for confirmation before printing')
    parser.add_argument('-d', '--device', type=str, default='',
                        help='The printer\'s BLE address or advertisement name')
    parser.add_argument('-e', '--energy', type=str, 
                        help='Thermal energy. Between 0x0000 (light) and 0xffff (darker, default)',
                        default='0xffff')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Get text from argument or stdin
    if args.text:
        text = args.text
    else:
        text = sys.stdin.read().strip()
    
    # Replace literal '\n' with actual newlines
    text = text.replace('\\n', '\n')
    
    # Use temporary directory for image
    output_file = '/tmp/catprinter-text.png'
    
    # Run text_to_image.py to create the image
    text_to_image_cmd = [
        'python', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'text_to_image.py'),
        text,
        '-f', str(args.font_size),
        '-w', str(args.width),
        '-p', str(args.padding),
        '-o', output_file
    ]
    
    # Run the text_to_image.py script
    subprocess.run(text_to_image_cmd, check=True)
    
    # Now run print.py to print the image
    print_cmd = [
        'python', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'print.py'),
        output_file,
        '-b', args.img_binarization_algo,
        '-e', args.energy,
        '-l', 'debug'
    ]
    
    # Add optional arguments if specified
    if args.show_preview:
        print_cmd.append('-s')
    
    if args.device:
        print_cmd.extend(['-d', args.device])
    
    # Run the print.py script
    subprocess.run(print_cmd, check=True)
    
    print(f"Text has been printed from image: {output_file}")

if __name__ == '__main__':
    main() 