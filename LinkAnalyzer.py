from encodings.utf_8 import encode
import json
import math
import os

file = os.getcwd()
file = os.path.join(file, "search")

def ensure_int_keys(x):
    return {int(k): v for k, v in x}

class ConnectivityServer:
    def __init__(self):

        self.url_to_outlinks = {}
        self.url_to_inlinks = {}

    def add_link(self, from_url, to_url):

        if from_url not in self.url_to_outlinks:
            self.url_to_outlinks[from_url] = []
        self.url_to_outlinks[from_url].append(to_url)

        if to_url not in self.url_to_inlinks:
            self.url_to_inlinks[to_url] = []
        self.url_to_inlinks[to_url].append(from_url)

    def get_outlinks(self, url):
        if url in self.url_to_outlinks:
            return self.url_to_outlinks[url]
        return []

    def get_inlinks(self, url):
        if url in self.url_to_inlinks:
            return self.url_to_inlinks[url]
        return []

# Read data from JSON file
with open(os.path.join(file, f"docs.txt"), 'r') as json_file:
    link_index_to_url = json.load(json_file, object_pairs_hook=ensure_int_keys)

for index in link_index_to_url:
    index = int(index)

link_url_to_index = {}

for key, value in link_index_to_url.items():
    link_url_to_index[value] = int(key)

with open(os.path.join(file, f"LinksInDocs.txt"), 'r') as txt_file:
    lines = txt_file.readlines()

connectivity_server = ConnectivityServer()
for line in lines:
    index = int(line[:line.find(":")])
    line = line[line.find(":")+1:]
    outlinks = line.split(";")
    for outlink in outlinks:
        if outlink in link_url_to_index:
            connectivity_server.add_link(index, link_url_to_index[outlink])

class PageRankCalculator:
    def __init__(self, connectivity_server, damping_factor=0.85, max_iterations=100, convergence_threshold=1e-5):
        self.connectivity_server = connectivity_server
        self.damping_factor = damping_factor
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold

    def calculate_page_rank(self):
        num_pages = len(self.connectivity_server.url_to_outlinks)
        initial_page_rank = 1 / num_pages

        page_ranks = {url: initial_page_rank for url in self.connectivity_server.url_to_outlinks}

        for iteration in range(self.max_iterations):
            new_page_ranks = {}

            for url in page_ranks:
                new_page_rank = (1 - self.damping_factor)

                calc = 0.0
                for inlink in self.connectivity_server.get_inlinks(url):
                    calc += page_ranks[inlink]/len(self.connectivity_server.url_to_outlinks[inlink])
                calc *= self.damping_factor
                new_page_rank += calc

                new_page_ranks[url] = new_page_rank

            page_ranks = new_page_ranks
        
        for key, value in page_ranks.items():
            page_ranks[key] = math.log(math.log(value+1.0)+1.0)
        return page_ranks

page_rank_calculator = PageRankCalculator(connectivity_server)
page_ranks = page_rank_calculator.calculate_page_rank()

with open("page_ranks.txt", 'w') as f:
    for url, score in sorted(page_ranks.items(), key=lambda x: x[1], reverse=True):
        f.write(f"{url},{score}\n")

with open("out_links.txt", 'wb') as f:
    for url, outlinks in connectivity_server.url_to_outlinks.items():
        f.write(f"{url};".encode())
        for outlink in outlinks:
            f.write(f"{outlink},".encode())
        f.seek(-1, 1)
        f.write(f"\n".encode())

with open("in_links.txt", 'wb') as f:
    for url, inlinks in connectivity_server.url_to_inlinks.items():
        f.write(f"{url};".encode())
        for inlink in inlinks:
            f.write(f"{inlink},".encode())
        f.seek(-1, 1)
        f.write(f"\n".encode())