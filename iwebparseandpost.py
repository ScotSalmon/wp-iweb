#!/usr/local/bin/python3

import argparse
import json
import os
import requests
import urllib
import logging
from datetime import datetime
from html.parser import HTMLParser

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

class iWebHTMLParser(HTMLParser):

    def __init__(self):
        super(iWebHTMLParser, self).__init__(convert_charrefs=False)
        self.recording = False
        self.in_title = False
        self.in_date = False
        self.cur_line = 0
        self.output = ''
        self.images = []
        self.featured_image = None
        
    def handle_starttag(self, tag, attrs):
        line, col = self.getpos()
        if line > self.cur_line:
            self.cur_line = line
            if self.recording:
                self.output += '\n'
        if tag == 'p':
            for name, value in attrs:
                if name == 'class':
                    if value == 'Title' or value == 'Heading_1':
                        self.recording = False
                        self.in_title = True
                        return
                    if value == 'Date' or value == 'Comment_Posted_Date':
                        self.recording = False
                        self.in_date = True
                        return
                    if value == 'Header':
                        # skip stray Normal block in circa 2011 output
                        self.recording = False
                        return
        if self.recording:
            self.depth += 1
            self.output += self.get_starttag_text()
        if tag == 'div':
            for name, value in attrs:
                if name == 'class' and (value == 'Normal' or value == 'style'):
                    self.recording = True
                    self.depth = 1

    def handle_endtag(self, tag):
        if self.in_title:
            self.in_title = False
        if self.in_date:
            self.in_date = False
        if self.recording:
            self.depth -= 1
            if self.depth == 0:
                self.recording = False
            else:
                self.output += '</' + tag + '>'

    def handle_startendtag(self, tag, attrs):
        if self.recording:
            if tag == 'img':
                for name, value in attrs:
                    if name == 'src' and not value.startswith('http'):
                        self.images.append(urllib.parse.unquote(value))
                        # iWeb: <img src="<day>_<title>_files/IMG_2996.jpg" alt="" style="border: none; height: 267px; width: 201px; " />
                        # WP: <img class="alignnone size-full wp-image-26" src="https://<site>.files.wordpress.com/2017/08/img_2993.jpg" alt="IMG_2993" width="367" height="275" />
                        img_dir = os.path.dirname(value)
                        wp_files_url = 'WP_IMAGE_PLACEHOLDER'
                        corrected_img = self.get_starttag_text().replace(img_dir, wp_files_url)
                        self.output += corrected_img
                        return
            self.output += self.get_starttag_text()
        else:
            if tag == 'img':
                attrs_dict = dict(attrs)
                # the featured has a special id tag
                if 'id' in attrs_dict and attrs_dict['id'] == 'generic-picture-attributes':
                    if self.featured_image:
                        raise RuntimeError('multiple featured images?!')
                    self.featured_image = urllib.parse.unquote(attrs_dict['src'])
                # in circa-2011 iWeb output, they made the post title into an image so they could
                # make it look extra fancy; the image is always <post>_files/shapeimage_2.png, and
                # always has the title as its alt text, and other shapeimage_2's from other eras
                # don't have alt text, so we can dig the title out that way
                if attrs_dict['src'].endswith('_files/shapeimage_2.png') and attrs_dict['alt'] != '':
                    self.title = attrs_dict['alt']

    def handle_data(self, data):
        if self.in_title:
            self.title = data
        if self.in_date:
            self.date = data
        if self.recording and len(data.strip()) > 0:
            self.output += data

    def handle_entityref(self, name):
        if self.recording:
            self.output += '&' + name + ';'

    def handle_charref(self, name):
        if self.recording:
            self.output += '&#' + name + ';'

def parse_entry(iweb_entry_html, wp_auth_token, wp_site):
    logging.info(iweb_entry_html + ' started')
    parser = iWebHTMLParser()
    with open(iweb_entry_html,'r') as f:
        html_string = f.read()
    parser.feed(html_string)

    post_datetime = datetime.strptime(parser.date, '%A, %B %d, %Y')
    post_datestr = str(post_datetime.date())
    slug = os.path.basename(iweb_entry_html)
    slug = slug.partition('_')[2] # strip off the day-of-month in the slug since WP's URL already has it
    slug = os.path.splitext(slug)[0]
    content = parser.output
    img_root = os.path.dirname(iweb_entry_html)
    img_array = [img_root + '/' + img_name for img_name in parser.images]
    logging.debug(img_array)
    logging.debug('title=' + parser.title)
    logging.debug('date=' + post_datestr)
    #logging.debug('content=' + content)
    logging.debug('slug=' + slug)

    # format request inputs
    auth_header = {'Authorization': 'Bearer ' + wp_auth_token}

    # Including media in the post doesn't get the date correct: it uses today's date,
    # so if there are multiple blog entries with the same image name from different
    # dates, they'll conflict...I tried adding them after the posts/new in an edit
    # and that didn't help, and I don't see a way to get it to obey the post date
    # in the API like it does in the web uploader. Instead, just post the images
    # up front and track their actual URL's (WP will uniquify if needed) in the
    # response text (ugh).
    if img_array:
        files = []
        for index,img_path in enumerate(img_array):
            files.append(('media[{}]'.format(index), open(img_path, 'rb')))

        # seems we can only do 20 files at a time
        for i in range(0, len(files), 20):
            sub_files = files[i : i+20]
            sub_iweb_image_links = parser.images[i : i+20]
            r = requests.post(
                'https://public-api.wordpress.com/rest/v1.1/sites/' + wp_site + '.wordpress.com/media/new',
                files=sub_files,
                headers=auth_header)
            r.raise_for_status()

            response = r.json()
            for index,img_name in enumerate(sub_iweb_image_links):
                img_name = os.path.basename(img_name)
                content = content.replace('WP_IMAGE_PLACEHOLDER/' + img_name, response['media'][index]['URL'])

    if parser.featured_image:
        files = [('media[]', open(img_root + '/' + parser.featured_image, 'rb'))]
        r = requests.post(
            'https://public-api.wordpress.com/rest/v1.1/sites/' + wp_site + '.wordpress.com/media/new',
            files=files,
            headers=auth_header)
        r.raise_for_status()
        response = r.json()
        logging.debug(response)
        featured_image_id = response['media'][0]['ID']

    # now make the actual post
    payload = {'title': parser.title, 'date': post_datestr, 'content': content, 'slug': slug}
    if parser.featured_image:
        payload['featured_image'] = featured_image_id
    r = requests.post(
        'https://public-api.wordpress.com/rest/v1.1/sites/' + wp_site + '.wordpress.com/posts/new',
        data=payload,
        headers=auth_header)
    r.raise_for_status()

    response = r.json()
    post_id = str(response['ID'])
    logging.info(iweb_entry_html + ' posted, post_ID is ' + post_id)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('iweb_entry_html', help='path to HTML file for iWeb blog entry')
    parser.add_argument('wp_auth_token', help='your bearer token for the WordPress API')
    parser.add_argument('wp_site', help='your WordPress site name')
    args = parser.parse_args()
    parse_entry(args.iweb_entry_html, args.wp_auth_token, args.wp_site)

