from xxhash import xxh64
import numpy as np

from tokenizer import computeFrequencies, test_computeFrequencies, tokenize

def simhash(freqMap):
    HASHSIZE = 64

    tokenWeightedVector = np.zeros(HASHSIZE, dtype=np.int64)

    for key, freq in freqMap.items():
        hash_value = xxh64(key).intdigest()
        hash_bin = np.array(list(bin(hash_value)[2:].zfill(HASHSIZE)), dtype=np.int64)

        tokenWeightedVector += np.where(hash_bin, freq, -freq)

    return "".join("1" if x >= 0 else "0" for x in reversed(tokenWeightedVector))

def hashCompare(hashA, hashB):
    sameBitCount = 0.0
    for i in range(len(hashA)): # Count number of bits that are the same between the two. Return the percentage that are the same.
        if hashA[i] == hashB[i]:
            sameBitCount += 1.0
    
    return (sameBitCount / len(hashA))

def isSiteSimilarToPreviousSites(tokenLen, siteHash, previousSites, index, url):
    similarityRatio = 0.7
    while similarityRatio < 0.96 and (tokenLen > 64): # Adjust similarity ratio based on size of tokens
        tokenLen = tokenLen / 2
        similarityRatio = similarityRatio**(3/4)

    for i in range(index+1):  # Check if site is too similar to some number of previous sites
        if previousSites[i] is None:
            continue
        h = hashCompare(siteHash, previousSites[i])
        # print(h, end=" ")
        if h >= similarityRatio:
            # print(f"Skipping, same as {i}: {url}")
            return True
    return False