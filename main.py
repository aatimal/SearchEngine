from index import *

if __name__ == "__main__":
    index = InvertedIndex("a")
    index.CreateIndex()

    index.setUpSeekPoints()

    print("Done!", flush=True)
    # with open("index.txt", "w") as f:
    #     f.write(str(index))
    # with open("docs.txt", "w") as f:
    #     f.write(index.getDocumentMapping())
    # with open("results.txt", "w") as f:
    #     f.write(f"Number of documents: {str(index.getNumberOfDocuments())},\n")
    #     f.write(f"Number of tokens: {str(index.getNumberOfTokens())},\n")
    #     totalBytes = 0
    #     totalBytes += os.stat("index.txt").st_size
    #     totalBytes += os.stat("docs.txt").st_size
    #     f.write(f"Size of index: {str(totalBytes/1000)}KB")