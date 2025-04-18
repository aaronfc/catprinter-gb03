#!/usr/bin/env python3
import os
import sys
import requests
import time
import json
import subprocess
import argparse
from datetime import datetime, timedelta, timezone

def parse_args():
    parser = argparse.ArgumentParser(description='Server that listens for webhook events and prints messages')
    parser.add_argument('--webhook-url', type=str, required=True,
                       help='Your webhook URL from webhook.site')
    parser.add_argument('--check-interval', type=int, default=10,
                       help='How often to check for new messages in seconds (default: 10)')
    parser.add_argument('--timestamp-file', type=str, default='.webhook_timestamp',
                       help='File to store the timestamp of the last processed message')
    parser.add_argument('--print-args', type=str, default='',
                       help='Additional arguments to pass to print-text.py')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode to show detailed responses')
    parser.add_argument('--start-from', type=str,
                       help='Start processing from this UTC time (format: YYYY-MM-DDTHH:MM:SS)')
    parser.add_argument('--max-length', type=int, default=255,
                       help='Maximum character length for printed messages (default: 255)')
    parser.add_argument('--no-truncate', action='store_true',
                       help='Do not truncate messages regardless of length')
    return parser.parse_args()

def get_last_timestamp(timestamp_file):
    """Get the timestamp of the last processed message"""
    if os.path.exists(timestamp_file):
        try:
            with open(timestamp_file, 'r') as f:
                timestamp_str = f.read().strip()
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).astimezone(timezone.utc)
        except Exception as e:
            print(f"Error reading timestamp file: {e}")
    return None

def save_timestamp(timestamp_file, timestamp):
    """Save the timestamp of the last processed message in UTC ISO format"""
    with open(timestamp_file, 'w') as f:
        if isinstance(timestamp, datetime):
            # Ensure timestamp is in UTC
            timestamp_utc = timestamp.astimezone(timezone.utc)
            f.write(timestamp_utc.isoformat())
        else:
            f.write(str(timestamp))

def print_message(message, print_args='', max_length=255):
    """Print a message using print-text.py with length limit"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print_script = os.path.join(script_dir, 'print-text.py')
    
    # Truncate message if needed
    if max_length > 0 and len(message) > max_length:
        truncated_message = message[:max_length - 3] + '...'
        print(f"Message truncated from {len(message)} to {len(truncated_message)} characters")
        message_to_print = truncated_message
    else:
        message_to_print = message
    
    cmd = [sys.executable, print_script]
    if print_args:
        cmd.extend(print_args.split())
    cmd.append(message_to_print)
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def extract_token_from_url(url):
    """Extract the token from the webhook URL"""
    return url.strip('/').split('/')[-1]

def is_valid_post_json_message(request, debug=False):
    """Check if the request is a valid POST with a 'message' in the JSON body"""
    # Check if it's a POST request
    if request.get('method', '').upper() != 'POST':
        return False
    
    # Check for JSON body with message field
    body = request.get('content', request.get('body', ''))
    if not body:
        return False
    
    try:
        # Parse body as JSON
        if isinstance(body, str):
            body_data = json.loads(body)
        else:
            body_data = body  # Already parsed
        
        # Check for message field
        return isinstance(body_data, dict) and 'message' in body_data
    except:
        return False

def extract_message(request):
    """Extract message from a request"""
    try:
        body = request.get('content', request.get('body', ''))
        if isinstance(body, str):
            body_data = json.loads(body)
        else:
            body_data = body
        return body_data.get('message', '')
    except:
        return None

def parse_webhook_timestamp(timestamp_str, debug=False):
    """Parse a timestamp string into a UTC datetime object
    
    webhook.site timestamps are in UTC but don't include timezone info.
    We need to explicitly set the timezone to UTC.
    """
    if debug:
        print(f"Parsing timestamp: {timestamp_str}")
    
    try:
        # Handle formats with and without timezone info
        if 'T' in timestamp_str:
            # ISO format
            if timestamp_str.endswith('Z'):
                # Already has UTC indicator
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            elif '+' in timestamp_str or '-' in timestamp_str and timestamp_str.rindex('-') > 10:
                # Has timezone info
                dt = datetime.fromisoformat(timestamp_str)
            else:
                # No timezone info, assume UTC
                dt = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
        else:
            # webhook.site format: "YYYY-MM-DD HH:MM:SS" - no timezone info but is UTC
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        
        # Ensure result is in UTC
        dt_utc = dt.astimezone(timezone.utc)
        
        if debug:
            print(f"Parsed to UTC: {dt_utc.isoformat()}")
        
        return dt_utc
        
    except Exception as e:
        if debug:
            print(f"Error parsing timestamp '{timestamp_str}': {e}")
        # Return a default timestamp far in the past
        return datetime(2000, 1, 1, tzinfo=timezone.utc)

def main():
    args = parse_args()
    
    print(f"Starting webhook printer server...")
    print(f"URL: {args.webhook_url}")
    print(f"Check interval: {args.check_interval} seconds")
    print(f"Only processing POST requests with JSON message payloads")
    
    # Get max message length
    max_length = 0 if args.no_truncate else args.max_length
    if max_length > 0:
        print(f"Messages will be truncated to {max_length} characters for printing")
    else:
        print("Message length will not be limited")
    
    # Extract token and set up API URL
    token = extract_token_from_url(args.webhook_url)
    api_url = f"https://webhook.site/token/{token}/requests"
    
    # Determine starting timestamp
    last_timestamp = None
    if args.start_from:
        try:
            last_timestamp = parse_webhook_timestamp(args.start_from, args.debug)
            print(f"Starting from provided time: {last_timestamp.isoformat()}")
        except Exception as e:
            print(f"Error parsing start time: {e}")
    
    if last_timestamp is None:
        last_timestamp = get_last_timestamp(args.timestamp_file)
    
    if last_timestamp is None:
        # Start from current time minus 1 minute
        last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=1)
        print(f"Starting from current time: {last_timestamp.isoformat()}")
    else:
        print(f"Resuming from: {last_timestamp.isoformat()}")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        while True:
            try:
                # Fetch new webhook data
                response = requests.get(api_url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if args.debug:
                    print(f"API request to: {api_url}")
                    print(f"Response status: {response.status_code}")
                
                # Extract request list
                requests_list = data.get('data', data if isinstance(data, list) else [])
                if not requests_list:
                    if args.debug:
                        print("No requests found")
                    time.sleep(args.check_interval)
                    continue
                
                # Track the most recent timestamp
                most_recent_timestamp = last_timestamp
                
                # Process new requests
                for req in requests_list:
                    if not isinstance(req, dict):
                        continue
                    
                    # Get and parse created_at timestamp
                    created_at_str = req.get('created_at')
                    if not created_at_str:
                        continue
                    
                    if args.debug:
                        print(f"Request timestamp from API: {created_at_str}")
                    
                    created_at = parse_webhook_timestamp(created_at_str, args.debug)
                    
                    # Skip if already processed
                    if created_at <= last_timestamp:
                        if args.debug:
                            print(f"Skipping request from {created_at.isoformat()}")
                            print(f"  Last processed: {last_timestamp.isoformat()}")
                            print(f"  Comparison: {created_at.timestamp()} <= {last_timestamp.timestamp()}")
                        continue
                    
                    # Update most recent timestamp
                    if created_at > most_recent_timestamp:
                        most_recent_timestamp = created_at
                    
                    # Check if valid POST with JSON message
                    if not is_valid_post_json_message(req, args.debug):
                        if args.debug:
                            print(f"Skipping invalid request type")
                        continue
                    
                    # Extract and print message
                    message = extract_message(req)
                    if message:
                        # Log the full message regardless of length
                        print(f"\n[{created_at.isoformat()}] New message ({len(message)} chars):")
                        print(message)
                        
                        try:
                            # Print with potential length limit
                            print_message(message, args.print_args, max_length)
                            print("Message printed successfully")
                        except Exception as e:
                            print(f"Error printing: {e}")
                
                # Update timestamp if newer messages were processed
                if most_recent_timestamp > last_timestamp:
                    last_timestamp = most_recent_timestamp
                    save_timestamp(args.timestamp_file, last_timestamp)
                    if args.debug:
                        print(f"Updated timestamp to: {last_timestamp.isoformat()}")
                
            except requests.RequestException as e:
                print(f"API error: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
                if args.debug:
                    import traceback
                    traceback.print_exc()
            
            # Wait before next check
            time.sleep(args.check_interval)
    
    except KeyboardInterrupt:
        print("\nServer stopped by user")

if __name__ == '__main__':
    main() 