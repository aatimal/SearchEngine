# Search Engine Project

This project is a search engine built using Python and Go. It features real-time search capabilities, efficient indexing, and sophisticated ranking algorithms. The Python components handle tokenization, parsing, and indexing, while Go powers the search functionality.

## Features

- **Text Tokenization and Stemming**: Extracts and normalizes text from web pages, including stemming to reduce words to their base forms, and forming n-grams to improve longer searches.
- **Multi-Tiered Indexing**: Utilizes a multi-tiered inverted index for efficient search and retrieval of documents.
- **Token Scoring**: Mainly uses tf-idf to emphasize query frequency, as well as considering token positioning and stylization (such as headers, bold, etc.) to assign higher relevance to important terms.
- **Duplicate Detection**: Uses SimHash to identify and avoid indexing near-duplicate content.
- **Dynamic Windowing & Order Accuracy**: Query terms are evaluated based on term frequency as well as ordering within documents.
- **Link Analysis**: Tracks and analyzes links for both PageRank and HITS (Hyperlink-Induced Topic Search) to improve ranking accuracy.

---

## Architecture Overview

### Indexing Process
The indexing component processes directories and files, generating a multi-tiered inverted index. Partial indexes are created and merged for scalability. The system offloads in-memory data to disk efficiently to handle large datasets.

### Tokenization and Text Processing
The tokenizer module extracts, normalizes, and stems tokens from HTML pages. Stop words are removed, and contractions are expanded based on predefined rules. Token frequencies are calculated and merged into a global frequency map.

### Link Analysis and Ranking
The link analysis module tracks both in-links and out-links, supporting ranking algorithms like PageRank and HITS. These algorithms help determine the authority and relevance of web pages.

### Duplicate Detection
SimHash fingerprints are generated to compare and detect near-duplicate pages, ensuring unique content in the index.

---

## Installation

1. Clone the repository:
    ```bash
        git clone https://github.com/aatimal/SearchEngine.git
    ```

2. Ensure Python and Go are installed

3. Install requirements.txt

4. Insert html scrapes into ./DEV folder

5. Run main.py to generate indexes, seekpoints, and data for PageRank and HITS

6. Use search.go


