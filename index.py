# Creates the inverted index map
import os, json, io, gc
from PageAnalyzer import getLinksFromFile, processPage, getStyleScore
from posting import Instance, Posting
from tokenizer import computeFrequencies
from collections import defaultdict
from collections.abc import Mapping, Container
from sys import getsizeof
from simhash import simhash, isSiteSimilarToPreviousSites
from typing import List

import numpy as np

from alive_progress import alive_bar

# A posting should typically contain 
# the document name/id the token was found in.
# and its tf-idf score for that document (for MS1, add only the term frequency) according to Assignment 3 document

SIM_HASH_COLLECTION_SIZE = 56000
SimHashCollection = [None] * SIM_HASH_COLLECTION_SIZE
SHCindex = 0

class InvertedIndex:

    def __init__(self, word):
        self.index_map: defaultdict[str, List[Posting]] = defaultdict(list)
        self.ID_map = {} # Maps doc names to doc Ids
        self.docID_count = 1 # Starts doc IDs at 1
        self.dev_directory = os.getcwd()
        self.dev_directory = os.path.join(self.dev_directory, "DEV")
        self.keyword = word
        self.index_size_count = 0
        self.max_index_size = 1000000
        self.offloadCount = 0
        self.corpus_size = 0
        self.token_num = 0

    def CreateIndex(self):
        self.CreatePartialIndexes()
        # input("Press enter")
        self.mergeIndex()
        # input("Press enter")
        wd = os.getcwd()
        p = os.path.join(wd, "search", "docs.txt")
        with open(p, "w+") as f:
            f.write(self.getDocumentMapping())

        lCount = 0
        wd = os.getcwd()
        # wd = os.path.join(wd, "Unmerged_Indexes")
        with open(os.path.join(wd, "Merged_Index.txt"), "r") as f:
            lCount = sum(1 for line in f)
        self.token_num = lCount

        self.calculateInverse()
        # input("Press enter")
        self.sortIndex()
        # input("Press enter")
        self.setUpSeekPoints("Sorted_Index.txt", "seek_points.txt")
        # input("Press enter")

    def CreatePartialIndexes(self):
        '''
        Goes through all directories and files in "DEV" file in alphabetical order. 
        Creates an inverted index of all tokens in all files.

        '''

        global simHashCollection
        global SimHashCollection
        global SHCindex
        global knownSimilarSites


        wd = os.getcwd()
        # wd = os.path.join(wd, "Unmerged_Indexes")
        if not (os.path.exists(wd)):
            os.makedirs(wd, exist_ok=True)

        # Get list of all directories in "DEV" folder in alphabetical order

        list_of_directories = sorted(os.listdir(self.dev_directory))[1:]

        count = 0
        
        for directory in list_of_directories:
            current_directory = os.path.join(self.dev_directory, directory)
            
            for dirpath, dirnames, all_files in os.walk(current_directory):
                count += len(all_files)
        
        self.corpus_size = count

        with alive_bar(count) as bar:
            bar.title = "Creating partial indexes"
            # Iterate through all directories.
            for directory in list_of_directories:
                current_directory = os.path.join(self.dev_directory, directory)
                # print(directory)

                # Go through all files in alphabetical order and tokenize them
                for dirpath, dirnames, all_files in os.walk(current_directory):
                    for file in sorted(all_files):
                        url = None
                        # Tokenize File Here
                        tokens = None
                        with open(os.path.join(dirpath, file), 'r') as f:
                            fileJSON = json.load(f)
                            tokens = processPage(fileJSON['content'])
                            url = fileJSON["url"]
                        
                            wordCount = len(tokens)
                            freq = computeFrequencies(tokens)

                            # Calculate the hash fingerprint for the frequency of words on the website.
                            siteHash = simhash(freq)

                            # If the site is similar to a previous site, prevent this site from being indexed
                            if isSiteSimilarToPreviousSites(wordCount, siteHash, SimHashCollection, SHCindex, fileJSON['url']):
                                SimHashCollection[SHCindex] = siteHash
                                SHCindex = (SHCindex + 1) % SIM_HASH_COLLECTION_SIZE
                                continue
                            SimHashCollection[SHCindex] = siteHash
                            SHCindex = (SHCindex + 1) % SIM_HASH_COLLECTION_SIZE

                            
                            add_new_url = False
                            # Add Tokens To Inverted Index Here
                            if url not in self.ID_map.values():
                                add_new_url = True
                                self.ID_map[self.docID_count] = url
                            tokens.sort(key=lambda x: x['word'])
                            word = ""
                            for token in tokens:
                                if token['word'] == word:
                                    self.index_map[token['word']][-1].addInstance(Instance(token['position'], getStyleScore(token)))
                                else:
                                    word = token['word']
                                    posting = Posting(self.docID_count, 1 + np.log(freq[token['word']]+1), [Instance(token['position'], getStyleScore(token))])
                                    self.index_map[token['word']].append(posting)
                                    self.index_size_count += 1

                            if add_new_url:
                                self.docID_count += 1
                            if self.index_size_count > self.max_index_size:
                                self.offloadIndex()

                            bar()
            self.offloadIndex()

    def getDocumentMapping(self):
        result = io.StringIO()
        result.write("{\n")
        for key in self.ID_map:
            result.write(f'"{key}": "{str(self.ID_map[key])}",\n')
        result.seek(result.tell()-2, os.SEEK_SET)
        result.write("\n}")
        out = result.getvalue()
        result.close()
        return out

    # Overrridden print method for InvertedIndex 
    def __str__(self):
        sortedIndex = sorted(self.index_map.items(), key = lambda x:(x[0]))
        sortedIndex = dict(sortedIndex) 
        result = io.StringIO()
        for key in sortedIndex:
            result.write(f"{key}:")
            for posting in sortedIndex[key]:
                result.write(f"{posting};")
            result.seek(result.tell()-1, os.SEEK_SET)
            result.write(f"\n")
        out = result.getvalue()
        result.close()
        return out
    

    def mergeIndex(self):
        '''
        Merges all indexes in Unmerged_Indexes into a single index

        return: None

        '''
        #TODO: Read index_map 1 key at a time and read inverted_index.txt 1 line at a time.
        #      Compare the token and see which one will appear first in alphabetical order
        filesToMerge = self.offloadCount

        items = filesToMerge
        itemsCount = 0
        while items > 1:
            count = 0
            for i in range(0, int(items), 2):
                count += 1
                itemsCount += 1
            items = count

        with alive_bar(itemsCount) as bar:
            bar.title = "Merging partial indexes"
            while filesToMerge > 1:
                # print(f"filesToMerge: {filesToMerge}")
                count = 0
                for i in range(0, int(filesToMerge), 2):
                    count += 1
                    self.merge(i, i + 1 if i + 1 < filesToMerge else None)
                    # print(f"Merging {i} and {i+1}")
                    bar()
                filesToMerge = count
        
        wd = os.getcwd()
        # wd = os.path.join(wd, "Unmerged_Indexes")
        
        if (os.path.exists(os.path.join(wd, f"Merged_Index.txt"))):
            os.remove(os.path.join(wd, f"Merged_Index.txt"))
        os.rename(os.path.join(wd, f"index_0.txt"), os.path.join(wd, f"Merged_Index.txt"))

    def merge(self, file1, file2):
        wd = os.getcwd()
        # wd = os.path.join(wd, "Unmerged_Indexes")
        
        if file2 is None:
            os.rename(os.path.join(wd, f"index_{file1}.txt"), os.path.join(wd, f"index_{int(file1/2)}.txt"))
            return
        
        with open(os.path.join(wd, f"index_{file1}.txt"), "r") as f1:
            with open(os.path.join(wd, f"index_{file2}.txt"), "r") as f2:
                with open(os.path.join(wd, "index_merging.txt"), "w") as wf:
                    word1, line1, posts1 = self.getWord(f1)
                    word2, line2, posts2 = self.getWord(f2)

                    while True:
                        # print(f"{word1}: {line1}")
                        # print(f"{word2}: {line2}")
                        if word1 is None:
                            l = line2
                            while l:
                                wf.write(l)
                                l = f2.readline()
                            break
                        if word2 is None:
                            l = line1
                            while l:
                                wf.write(l)
                                l = f1.readline()
                            break
                        if word1 == word2:
                            wf.write(f"{word1}:")
                            lineA = line1[line1.find(':')+1:len(line1)-1]
                            wf.write(lineA)
                            wf.write(";")
                            lineB = line2[line2.find(':')+1:]

                            # print(f"M: {lineA}")
                            # print(f"M: {lineB}")

                            wf.write(lineB)
                            word1, line1, posts1 = self.getWord(f1)
                            word2, line2, posts2 = self.getWord(f2)
                        elif word1 > word2:
                            wf.write(line2)
                            word2, line2, posts2 = self.getWord(f2)
                        elif word1 < word2:
                            wf.write(line1)
                            word1, line1, posts1 = self.getWord(f1)
        os.remove(os.path.join(wd, f"index_{file1}.txt"))
        os.remove(os.path.join(wd, f"index_{file2}.txt"))
        # print(f"renaming index_merging.txt to index_{int(file1/2)}.txt")
        os.rename(os.path.join(wd, f"index_merging.txt"), os.path.join(wd, f"index_{int(file1/2)}.txt"))
    
    def calculateInverse(self):
        wd = os.getcwd()
        # wd = os.path.join(wd, "Unmerged_Indexes")
        with alive_bar(self.token_num) as bar:
            bar.title = "Calculating inverse document frequency"
            with open(os.path.join(wd, "calculating_index.txt"), "w") as w:
                with open(os.path.join(wd, "Merged_Index.txt"), "r") as f:
                    word1, line1, posts = self.getWord(f)
                    while True:
                        if word1 is None:
                            break
                        postings = []
                        for post in posts:
                            fields = post.split("=")
                            docID = fields[0].split(",")
                            tf = docID[1]
                            docID = docID[0]
                            fields = fields[1].split("|")
                            posting = Posting(int(docID), float(tf), [])
                            for field in fields:
                                position = field.split(",")
                                styleScore = position[1]
                                position = position[0]
                                posting.addInstance(Instance(int(position), int(styleScore)))
                            postings.append(posting)

                        number_of_docs_with_word = len(postings)

                        idf = (self.corpus_size)/(1+number_of_docs_with_word)
                        idf = np.log(idf)

                        w.write(f"{word1},{idf}:")
                        for post in postings:
                            w.write(f"{post};")
                        w.seek(w.tell()-1, os.SEEK_SET)
                        w.write(f"\n")
                        word1, line1, posts = self.getWord(f)
                        bar()
        os.remove(os.path.join(wd, f"Merged_Index.txt"))
        os.rename(os.path.join(wd, f"calculating_index.txt"), os.path.join(wd, f"Merged_Index.txt"))


    def getWord(self, file):
        line = file.readline()
        if not line:
            return None, None, None
        word = line[:line.find(":")]
        posts = line[line.find(":")+1:]
        posts = posts.split(";")
        return word, line, posts

    def sortIndex(self):
        wd = os.getcwd()
        wd = os.path.join(wd, "Unmerged_Indexes")
        if (os.path.exists(os.path.join(wd, f"Sorted_Index.txt"))):
            os.remove(os.path.join(wd, f"Sorted_Index.txt"))        
        os.rename(os.path.join(wd, f"Merged_Index.txt"), os.path.join(wd, f"Sorted_Index.txt"))
        # with alive_bar(self.token_num) as bar:
        #     bar.title = "Sorting indexes"
        #     with open(os.path.join(wd, "Merged_Index.txt"), "r") as f:
        #         with open(os.path.join(wd, "Sorted_Index.txt"), "w") as w:
        #             word, line, posts = self.getWord(f)
        #             word = word.split(",")
        #             idf = word[1]
        #             word = word[0]
        #             while True:
        #                 if word is None:
        #                     break
        #                 postings = []
        #                 for post in posts:
        #                     fields = post.split("=")
        #                     docID = fields[0].split(",")
        #                     tf = docID[1]
        #                     docID = docID[0]
        #                     fields = fields[1].split("|")
        #                     posting = Posting(int(docID), float(tf))
        #                     for field in fields:
        #                         position = field.split(",")
        #                         styleScore = position[1]
        #                         position = position[0]
        #                         posting.addInstance(Instance(int(position), int(styleScore)))
        #                     postings.append(posting)
        #                 postings = sorted(postings, key=lambda x: (x.docID))


        #                 w.write(f"{word},{idf}:")
        #                 for post in postings:
        #                     w.write(f"{post};")
        #                 w.seek(w.tell()-1, os.SEEK_SET)
        #                 w.write(f"\n")

        #                 word, line, posts = self.getWord(f)
        #                 bar()


    def offloadIndex(self):
        '''
        Offload index_map by inserting it into a file.
        Clear the used memory by making index_map empty, then using the garbage collection 
        library to free up memory
        
        return: None

        '''

        # Open file for writing and insert Posting info for each token in dict format
        file = os.getcwd()
        # file = os.path.join(file, "Unmerged_Indexes")
        file = os.path.join(file, f"index_{self.offloadCount}.txt")
        # print(f"{file}", flush=True)
        with open(file, "w") as f:
            f.write(self.__str__())
                
        self.offloadCount += 1
        self.index_size_count = 0
        
        mapsize = self.deep_getsizeof(self.index_map, set())
        sizeindisk = os.stat(file).st_size
        
        # Clear index_map from program memory 
        self.index_map.clear()
        gc.collect()

        if (mapsize > 1000):
            mapsize = mapsize / 1000
            if (mapsize > 1000):
                mapsize = mapsize / 1000
                print(f"Offloaded {round(mapsize, 2)} MB off memory onto disk.")
            else:
                print(f"Offloaded {round(mapsize, 2)} KB off memory onto disk.")
        else:
            print(f"Offloaded {mapsize} bytes off memory onto disk.")
        if (sizeindisk > 1000):
            sizeindisk = sizeindisk / 1000
            if (sizeindisk > 1000):
                sizeindisk = sizeindisk / 1000
                print(f"Size in disk: {round(sizeindisk, 2)} MB")
            else:
                print(f"Size in disk: {round(sizeindisk, 2)} KB")
        else:
            print(f"Size in disk: {sizeindisk} bytes")

    ### From https://code.tutsplus.com/understand-how-much-memory-your-python-objects-use--cms-25609t
    ### with minor modifications, Date of retrieval: 11/15/23
    def deep_getsizeof(self, o, ids):
        """Find the memory footprint of a Python object

        This is a recursive function that rills down a Python object graph
        like a dictionary holding nested ditionaries with lists of lists
        and tuples and sets.

        The sys.getsizeof function does a shallow size of only. It counts each
        object inside a container as pointer only regardless of how big it
        really is.

        :param o: the object
        :param ids:
        :return:
        """
        d = self.deep_getsizeof
        if id(o) in ids:
            return 0

        r = getsizeof(o)
        ids.add(id(o))

        if isinstance(o, Mapping):
            return r + sum(d(k, ids) + d(v, ids) for k, v in o.items())

        if isinstance(o, Container):
            return r + sum(d(x, ids) for x in o)

        return r
    
    def setUpSeekPoints(self, file_to_seek, seek_save_file):
        wd = os.getcwd()
        wd = os.path.join(wd, "search")
        with alive_bar(self.token_num) as bar:
            bar.title = "Setting up seek points"
            with open(os.path.join(wd, "seekpoints.txt"), "w+") as w:
                with open(os.path.join(wd, "Sorted_Index.txt"), "r") as wordf:
                    with open(os.path.join(wd, "Sorted_Index.txt"), "rb") as f:
                        bytecount = 0
                        word, l, posts = self.getWord(wordf)
                        word = word.split(",")[0]
                        w.write(f"{word},{bytecount}\n")
                        c = b'a'
                        while c:
                            c = f.read(1)
                            bytecount += 1
                            if c == b'\n':
                                word, l, posts = self.getWord(wordf)
                                if (word != None):
                                    word = word.split(",")[0]
                                    w.write(f"{word},{bytecount}\n")
                                bar()

    def createTieredIndex(self):
        htfs = []
        wd = os.getcwd()
        wd = os.path.join(wd, "Unmerged_Indexes")
        with alive_bar() as bar:
            bar.title = "Creating tiered indexes"
            with open(os.path.join(wd, "Sorted_Index.txt"), "r") as r:
                with open(os.path.join(wd, "Tier_1_Index.txt"), "w") as f1:
                    with open(os.path.join(wd, "Tier_2_Index.txt"), "w") as f2:
                        with open(os.path.join(wd, "Tier_3_Index.txt"), "w") as f3:
                            word, line, posts = self.getWord(r)
                            word = word.split(",")
                            idf = word[1]
                            word = word[0]
                            while True:
                                if word is None:
                                    break
                                postings = []
                                for post in posts:
                                    fields = post.split("=")
                                    docID = fields[0].split(",")
                                    tf = docID[1]
                                    docID = docID[0]
                                    fields = fields[1].split("|")
                                    posting = Posting(int(docID), float(tf), [])
                                    for field in fields:
                                        position = field.split(",")
                                        styleScore = position[1]
                                        position = position[0]
                                        posting.addInstance(Instance(int(position), int(styleScore)))
                                    postings.append(posting)

                                f1.write(f"{word},{idf}:")
                                f2.write(f"{word},{idf}:")
                                f3.write(f"{word},{idf}:")

                                for post in postings:
                                    if post.tfScore >= 7:
                                        f1.write(f"{post};")
                                    elif 3 <= post.tfScore < 7:
                                        f2.write(f"{post};")
                                    else:
                                        f3.write(f"{post};")

                                f1.seek(f1.tell()-1, os.SEEK_SET)
                                f1.write(f"\n")
                                f2.seek(f2.tell()-1, os.SEEK_SET)
                                f2.write(f"\n")
                                f3.seek(f3.tell()-1, os.SEEK_SET)
                                f3.write(f"\n")

                                word, line, posts = self.getWord(r)
                                if word:
                                    word = word.split(",")
                                    idf = word[1]
                                    word = word[0]
                                bar()

# if __name__ == "__main__":
#     index = InvertedIndex("a")
#     index.CreateIndex()
#     print("Done!", flush=True)
#     with open("index.txt", "w") as f:
#         f.write(str(index))
#     with open("docs.txt", "w") as f:
#         f.write(index.getDocumentMapping())
#     with open("results.txt", "w") as f:
#         f.write(f"Number of documents: {str(index.getNumberOfDocuments())},\n")
#         f.write(f"Number of tokens: {str(index.getNumberOfTokens())},\n")
#         totalBytes = 0
#         totalBytes += os.stat("index.txt").st_size
#         totalBytes += os.stat("docs.txt").st_size
#         f.write(f"Size of index: {str(totalBytes/1000)}KB")



if __name__ == "__main__":
    index = InvertedIndex("a")
    index.CreateIndex()
    # index.calculateInverse()
    # index.setUpSeekPoints()
    # index.createTieredIndex()
