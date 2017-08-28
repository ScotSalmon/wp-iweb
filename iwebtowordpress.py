#!/usr/local/bin/python3

import argparse
import glob
import logging
import os
import urllib
import iwebparseandpost

parser = argparse.ArgumentParser()
parser.add_argument('iweb_blog_path', help='path root directory of iWeb blog')
parser.add_argument('wp_auth_token', help='your bearer token for the WordPress API')
parser.add_argument('wp_site', help='your WordPress site name')
args = parser.parse_args()

with open(args.iweb_blog_path + '/index.html','r') as f:
    html_string = f.read()
start_pos = html_string.find('url=') + 4
end_pos = html_string.find('"', start_pos)
blog_main = urllib.parse.unquote(html_string[start_pos:end_pos].strip())
blog_entries_root = args.iweb_blog_path + '/' + os.path.dirname(blog_main) + '/Entries'
blog_entries = glob.glob(blog_entries_root + '/*/*/*.html')
logging.debug(blog_entries)

for entry in blog_entries:
    iwebparseandpost.parse_entry(entry, args.wp_auth_token, args.wp_site)
