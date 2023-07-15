#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import string

import requests as rq
import argparse
import sys
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import re

# Parse input
Usage = ("""{}SANS Txt to Index
Use pdftotext to convert a SANS PDF to a txt file, then generate its index here.
Usage:
\t-i, --input-file: txt file of SANS book.
\t-o, --output-file: file to save new index at.
\t-n, --student-name: full name of student, used to split pages by delimiter.
""")

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input-file", help="txt file of SANS book.")
parser.add_argument("-o", "--output-file", help="output file of index.")
parser.add_argument("-n", "--student-name", help="full name of student.")
parser.add_argument("-m", "--mode", help="f for stop word removal mode, otherwise common word removal mode", nargs='?',
                    default=None)
options = parser.parse_args(sys.argv[1:])

if not options.input_file:
    exit(Usage.format("Please enter an index file.\n"))

if not options.output_file:
    options.output_file = options.input_file.replace(".pdf", "") + ".txt"

delimeter = "Licensed To: "
if options.student_name:
    delimeter += options.student_name
# Get common english words
common_word_mode = True
if options.mode and options.mode == 'f':
    print("NLTK stop word removal mode")
    common_word_mode = False
else:
    print("Common word removal mode")
    common_words = rq.get(
        "https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-no-swears.txt").text.split(
        "\n")
# function to recursively strip given characters in a word
characters_to_strip = "–!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~—‘’“”•… "
# http regex from https://www.makeuseof.com/regular-expressions-validate-url/
http_url_regex = "^((http|https)://)[-a-zA-Z0-9@:%._\\+~#?&//=]{2,256}\\.[a-z]{2,6}\\b([-a-zA-Z0-9@:%._\\+~#?&//=]*)$"
# url regex adapted from https://uibakery.io/regex-library/url-regex-python
url_regex = "^(((http|https)://)|(www\\.))[-a-zA-Z0-9@:%._\\+~#?&//=]{2,256}\\.[a-z]{2,6}\\b([-a-zA-Z0-9@:%._\\+~#?&//=]*)$"
# non http one from https://uibakery.io/regex-library/url-regex-python is less restrictive and matches on file names and such too
stop_words = [sw.translate(str.maketrans('', '', string.punctuation)) for sw in stopwords.words('english')]


def strip_characters(in_word):
    in_word = in_word.strip(characters_to_strip)
    http_url_pattern = re.compile(http_url_regex)
    url_pattern = re.compile(url_regex)
    if http_url_pattern.match(in_word):
        return in_word
    elif url_pattern.match(in_word):
        return in_word
    wnl = WordNetLemmatizer()
    in_word = in_word.translate(str.maketrans('', '', characters_to_strip + '0123456789'))
    return wnl.lemmatize(in_word)


# Check that word should be added to index
def word_is_eligible(in_word):
    # Length check
    if 3 > len(in_word):
        return False
    # Starts with number
    if in_word.isdigit():
        return False
    # Not common english word
    if common_word_mode:
        if in_word.lower() in common_words or in_word.lower() + "s" in common_words:
            return False
        if in_word.lower() in stop_words or in_word.lower() + "s" in stop_words:
            return False
    else:
        if in_word.lower() in stop_words or in_word.lower() + "s" in stop_words:
            return False
    # Not SANS url
    if in_word.startswith("http://") or in_word.startswith("https://"):
        return False
    return True


# Get pages in pdf
with open(options.input_file, "r") as f:
    data = f.read()
    pages = data.split(delimeter)[1:]

# Get words per page
# dict with word as key, set as int page nums
word_page_num_dict = {}
for page_idx, page in enumerate(pages):
    if page_idx == 0:
        continue
    if page_idx >= len(pages)-2:
        continue
    # Recursively replace whitespace with one singular space
    page = page.replace("\n", " ").replace("\t", " ")
    page_len = len(page)
    while True:
        page = page.replace("  ", " ")
        if len(page) == page_len:
            break
        else:
            page_len = len(page)
    # Trim whitespace
    page = page.strip()
    # Get words
    words = page.split(" ")
    word_tokenized = word_tokenize(page)
    for word in words:
        # Strip some punctuation
        word = strip_characters(word).lower()
        if word_is_eligible(word):
            temp_page_set = set(word_page_num_dict.get(word, set()).copy())
            temp_page_set.add(page_idx)
            word_page_num_dict[word] = sorted(temp_page_set)

# -- sorting logic, can alter depending on preference
#sorted_word_page_num_dict = dict(sorted(word_page_num_dict.items(), key=lambda item: (item[1], item[0])))
sorted_word_page_num_dict = dict(sorted(word_page_num_dict.items(), key=lambda item: (item[0], item[1])))

print()
# Write output to file
with open(options.output_file, "w") as f:
    for sorted_word_page_num_key, sorted_word_page_num_value in sorted_word_page_num_dict.items():
        if len(sorted_word_page_num_value) < 15:
            result = f"{sorted_word_page_num_key}: " \
                     f"{', '.join([str(pg_num_int) for pg_num_int in sorted_word_page_num_value])}"
            f.write(result + "\n")
print(f"Written index to {options.output_file}")
