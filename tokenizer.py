from collections import defaultdict
import re
import json
# from stop_words import stop_words_map


def tokenize(text):
    '''
    Retrieves text from HTML page and covnerts it to lowercase. Converts the text into a list and removes stop words.
    Then, find all contractions and subsitute the words from contractions.json. Tokenize the text and count the number
    of tokens. If number of tokens is greater than max_page_size, return empty list.

    return: tokenList.
    
    '''
    text = text.lower()
    text = re.sub(r"[']", "", text) 
    tokenList = re.findall(r"[0-9A-Za-z]+", text, re.DOTALL)
    
    return tokenList

def computeFrequencies(tokenList):
    '''
    Calculates the number of times a word appears within the tokenList.

    return: dictionary with frequency map.

    '''
    freqMap = {}
    for token in tokenList:
        if token['word'] in freqMap:
            freqMap[token['word']] += 1
        else:
            freqMap[token['word']] = 1
    return freqMap

def test_computeFrequencies(tokenList):
    '''
    Calculates the number of times a word appears within the tokenList.

    return: dictionary with frequency map.

    '''
    freqMap = {}
    for token in tokenList:
        if token in freqMap:
            freqMap[token] += 1
        else:
            freqMap[token] = 1
    return freqMap

def subsumeFreqMap(globalMap, localMap):
    '''
    Checks all tokens in local map and adds them to the global map.

    return: None, updates the global map with frequencies of tokens.
    
    '''
    for key in localMap:
        if key in globalMap:
            globalMap[key] += localMap[key]
        else:
            globalMap[key] = localMap[key]


def printFrequencies(tokenFrequencies):
    '''
    Prints the frequency of tokens from the sorted tokenFrequencies dictionary.

    return: None, prints output of tokenFrequencies.
    
    '''
    flippedMap = defaultdict(list)         # create a hash map that stores (count, list of tokens)
    for Frequencies in tokenFrequencies:   # instead of (token, count)
        flippedMap[tokenFrequencies[Frequencies]].append(Frequencies)
    flippedList = list(flippedMap.items()) # flatten dict
    for freqToken in flippedList:          # sort all list of tokens alphabetically
        freqToken[1].sort()
    flippedList.sort()         # sort list by frequency

    print("{", end="")
    for freqToken in reversed(flippedList):
        for token in freqToken[1]:
            print(token + ": " + str(freqToken[0]) + ", ", flush=False, end="")
    print("}", flush=True)