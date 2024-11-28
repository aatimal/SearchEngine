from collections import defaultdict
from urllib.parse import urldefrag, urljoin
from bs4 import BeautifulSoup, NavigableString, XMLParsedAsHTMLWarning, MarkupResemblesLocatorWarning
import html
import re
from enum import Enum
from nltk.stem import PorterStemmer

from tokenizer import tokenize

import warnings
warnings.filterwarnings("error")

porter = PorterStemmer()

class Style(Enum):
    TITLE = 'title'
    HEADING = 'heading'
    BOLD = 'bold'
    ITALICS = 'italics'
    ANCHOR = 'anchor'

def process_html_elements(element, is_heading=False, position=0, is_title=False, is_anchor=False, is_bold=False, is_italic=False):
    words_info = []

    if element.name:
        is_heading = element.name in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
        is_title = element.name in {'title'}
        is_anchor = element.name in {'a'}
        is_bold = element.name in {'b', 'mark', 'strong'}
        is_italic = element.name in {'i', 'em'}

    interesting_types = element.interesting_string_types
    for content in element.children:
        # print(f"{content.name}, {isinstance(content, interesting_types)}, {content.get_text()}")
        # print(f"---H:{is_heading}, T:{is_title}, A:{is_anchor}, B:{is_bold}, I:{is_italic}---")
        if isinstance(content, interesting_types):
            words = tokenize(content.get_text())
            for word in words:
                position += 1
                styles = []
                if is_title:
                    styles.append(Style.TITLE)
                if is_heading:
                    styles.append(Style.HEADING)
                if is_anchor:
                    styles.append(Style.ANCHOR)
                if is_bold:
                    styles.append(Style.BOLD)
                if is_italic:
                    styles.append(Style.ITALICS)
                
                words_info.append({
                    'word': word,
                    'position': position,
                    'styles': styles
                })
        elif content.name:
            text, position = process_html_elements(content, is_heading, position, is_title, is_anchor, is_bold, is_italic)
            words_info.extend(text)

    return words_info, position

def process_xml_elements(element, is_heading=False, position=0, is_title=False, is_anchor=False, is_bold=False, is_italic=False):
    words_info = []

    if element.name:
        is_heading = element.name in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'head', 'heading'} or element.name.startswith('sect')
        is_title = element.name in {'title'}
        is_anchor = element.name in {'a'}
        is_bold = element.name in {'b', 'mark', 'strong'}
        is_italic = element.name in {'i', 'em'}
        

    if isinstance(element, NavigableString):
        words = tokenize(element.get_text())
        for word in words:
            position += 1
            styles = []
            if is_title:
                styles.append(Style.TITLE)
            if is_heading:
                styles.append(Style.HEADING)
            if is_anchor:
                styles.append(Style.ANCHOR)
            if is_bold:
                styles.append(Style.BOLD)
            if is_italic:
                styles.append(Style.ITALICS)
            
            words_info.append({
                'word': word,
                'position': position,
                'styles': styles
            })
    elif hasattr(element, 'children'):
        for child in element.children:
            text, position = process_xml_elements(child, is_heading, position)
            words_info.extend(text)

    return words_info, position

def parse_html(html_content):
    decoded_content = html.unescape(html_content)
    soup = BeautifulSoup(decoded_content, 'lxml')
    words_info, _ = process_html_elements(soup)
    return words_info

def parse_xml(xml_content):
    decoded_content = html.unescape(xml_content)
    soup = BeautifulSoup(decoded_content, 'xml')
    words_info, _ = process_xml_elements(soup)
    return words_info

def parse_text(text_content):
    words_info = []
    position = 0
    words = tokenize(text_content)
    for word in words:
            position += 1            
            words_info.append({
                'word': word,
                'position': position,
                'styles': []
            })
    return words_info

def getStemmedTokens(tokens):
    stemmed = []
    for token in tokens:
        stem = porter.stem(token['word'])
        if stem != token['word']:
            stemmed.append({
                'word': porter.stem(token['word']),
                'position': token['position'],
                'styles': token['styles']
            })
        else:
            stemmed.append(None)
    return stemmed

def getNGram(tokens, stemmed_tokens, n):
    tokenGrams = []
    for i in range(0, len(tokens)-n+1):
        oldTokens = [""]
        newTokens = []

        position = None
        styles = []
        for j in range(0, n):
            if j == 0:
                position = tokens[i]['position']
            styles.append(tokens[i+j]['styles'])
            token_choices = []
            token_choices.append(tokens[i+j]['word'])
            if stemmed_tokens[i+j]:
                token_choices.append(stemmed_tokens[i+j]['word'])
            for choice in token_choices:
                for old_token in oldTokens:
                    if (j == n-1):
                        newTokens.append(old_token + choice)
                    else:
                        newTokens.append(old_token + choice + " ")
            oldTokens = newTokens
            newTokens = []

        m = defaultdict(int)
        for style in styles:
            for s in style:
                m[s] += 1
        gramStyles = []
        for key, value in m.items():
            if value == n:
                gramStyles.append(key)
        for token in oldTokens:
            tokenGrams.append({
                'word': token,
                'position': position,
                'styles': gramStyles
            })
    return tokenGrams

def getStyleScore(posting):
    ANCHOR_SCORE = 5
    TITLE_SCORE = 10
    HEADING_SCORE = 8
    BOLD_SCORE = 3
    ITALICS_SCORE = 2
    styleScore: int = 0
    for style in posting['styles']:
        if style is Style.ANCHOR:
            styleScore += ANCHOR_SCORE
        elif style is Style.TITLE:
            styleScore += TITLE_SCORE
        elif style is Style.HEADING:
            styleScore += HEADING_SCORE
        elif style is Style.BOLD:
            styleScore += BOLD_SCORE
        elif style is Style.ITALICS:
            styleScore += ITALICS_SCORE
    return styleScore

def processPage(content):
    tokens = []
    try:
        if r"<?xml" in content[0:10]:
            # print("Processing XML page...")
            tokens = parse_xml(content)
        else:
            # print("Processing HTML page...")
            tokens = parse_html(content)
    except XMLParsedAsHTMLWarning:
        # print("Processing XML page...")
        tokens = parse_xml(content)
    except MarkupResemblesLocatorWarning:
        # print("Processing text...")
        tokens = parse_text(content)

    stem_tokens = getStemmedTokens(tokens)
    tokenTwoGram = getNGram(tokens, stem_tokens, 2)
    tokenThreeGram = getNGram(tokens, stem_tokens, 3)

    tokens.extend(tokenTwoGram)
    tokens.extend(tokenThreeGram)
    return tokens

def getLinksFromFile(html_content, url):
    try:
        if r"<?xml" in html_content[0:10]:
            return []
        soup = BeautifulSoup(html_content, "lxml")
        links = set(
            urldefrag(urljoin(url, anchor.get('href')))[0]
            for anchor in soup.findAll('a', href=True)
        )
        return list(links)
    except Exception as e:
        return []