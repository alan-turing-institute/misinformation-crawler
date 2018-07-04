#! /usr/bin/env python

import argparse
import subprocess
import time
import random

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=__name__)
    parser.add_argument('--input-file',
        help='Input file with URLs to capture, one URL per line.')
    parser.add_argument('--start-line', type=int,
        help='Line number of first URL to capture.')
    parser.add_argument('--num-lines', type=int,
        help='Number of URLs to capture.')
    parser.add_argument('--user',
        help='User ID on webrecorder.io.')
    parser.add_argument('--collection',
        help='Collection name on webrecorder.io.')
    parser.add_argument('--session',
        help='Session ID on webrecorder.io.')

    args = parser.parse_args()
    mean_load_interval_seconds = 3
    max_jitter_seconds = 1


    session_base_url = "https://webrecorder.io/{}/{}/{}/record/".format(args.user, args.collection, args.session)

    with open(args.input_file, 'r') as f:
        line_num = 1
        stop_line = args.start_line + args.num_lines
        for capture_url in f:
            if line_num >= stop_line:
                break
            if line_num >= args.start_line:
                capture_url = capture_url.strip()
                print("{}: '{}'".format(line_num, capture_url))
                url = session_base_url + capture_url
                subprocess.call(['open', '--background', url])
                jitter_seconds = random.uniform(-max_jitter_seconds, max_jitter_seconds)
                delay_seconds = mean_load_interval_seconds + jitter_seconds
                time.sleep(delay_seconds)
            line_num = line_num + 1


if __name__ == "__main__":
    main()