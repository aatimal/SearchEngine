package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/gammazero/deque"
	"github.com/reiver/go-porterstemmer"
)

type Instance struct {
	position   int64
	styleScore int64
}

type Posting struct {
	docID     int64
	tf        float64
	instances []Instance
}

type Token struct {
	word     string
	idf      float64
	postings map[int]Posting
}

// output := "'" + strings.Join(stuff, `','`) + `'`
// fmt.Println(output)

func getTokenFromIndex(index *os.File, seek_point int64, word string, mult float64) Token {

	var token Token

	var l []byte = getLine(index, seek_point)

	var llen int = len(l)
	var w int = 0
	var t int = 0
	for i := 0; i < llen; i++ {
		if l[i] == ',' {
			t = i
		}
		if l[i] == ':' {
			w = i
			i = llen
		}
	}
	// fmt.Println(string(l))
	if string(l[0:t]) == word {
		token.word = string(l[0:t])
		token.idf, _ = strconv.ParseFloat(string(l[t+1:w]), 64)
		token.postings = make(map[int]Posting)
		var line string = string(l)
		line = line[strings.Index(line, ":")+1:]
		linePosts := strings.Split(line, ";")
		for _, post := range linePosts {
			var posting Posting
			post_string := strings.Split(post, "=")
			posting.docID, _ = strconv.ParseInt(post_string[0][:strings.Index(post_string[0], ",")], 10, 64)
			posting.tf, _ = strconv.ParseFloat(post_string[0][strings.Index(post_string[0], ",")+1:], 64)
			posting.instances = make([]Instance, 0)
			post_instances := strings.Split(post_string[1], "|")
			for _, instance := range post_instances {
				var i Instance
				i.position, _ = strconv.ParseInt(instance[:strings.Index(instance, ",")], 10, 64)
				i.styleScore, _ = strconv.ParseInt(instance[strings.Index(instance, ",")+1:], 10, 64)
				posting.instances = append(posting.instances, i)
			}
			posting.tf = posting.tf * mult
			token.postings[int(posting.docID)] = posting
		}
	}
	return token
}

func getLine(f io.ReadSeeker, seek_point int64) []byte {
	var input io.ReadSeeker = f
	if _, err := input.Seek(seek_point, 0); err != nil {
		log.Fatal(err)
	}

	r := bufio.NewReader(input)
	pos := seek_point
	data, err := r.ReadBytes('\n')
	pos += int64(len(data))
	if err == nil || err == io.EOF {
		if len(data) > 0 && data[len(data)-1] == '\n' {
			data = data[:len(data)-1]
		}
		if len(data) > 0 && data[len(data)-1] == '\r' {
			data = data[:len(data)-1]
		}
	}
	if err != nil {
		if err != io.EOF {
			log.Fatal(err)
		}
	}
	return data
}

func getNTopDocuments(docs map[int]float64, N int) (map[int]bool, map[int]float64) {
	type DocumentCount struct {
		docID int
		score float64
	}
	var documentCounts []DocumentCount

	for docID, score := range docs {
		documentCounts = append(documentCounts, DocumentCount{docID: docID, score: score})
	}

	// Sort in descending order
	sort.Slice(documentCounts, func(i, j int) bool {
		return documentCounts[i].score > documentCounts[j].score
	})

	// Get the top N documents
	if len(documentCounts) > N {
		documentCounts = documentCounts[:N]
	}

	var topNb map[int]bool = make(map[int]bool)
	var topNs map[int]float64 = make(map[int]float64)

	for _, doc := range documentCounts {
		topNb[doc.docID] = true
		topNs[doc.docID] = doc.score
	}
	return topNb, topNs
}

func search(input string) {

	jsonf, jerr := os.ReadFile("search/docs.txt")
	if jerr != nil {
		log.Fatal(jerr)
	}

	var jdata map[string]interface{}
	jerr = json.Unmarshal(jsonf, &jdata)

	file, err := os.Open("search/seek_points.txt")
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()

	var seek_points map[string]int64 = make(map[string]int64)
	seek_scanner := bufio.NewScanner(file)
	for seek_scanner.Scan() {
		var line string = seek_scanner.Text()
		var word string = line[:strings.Index(line, ",")]
		line = line[strings.Index(line, ",")+1:]
		num, _ := strconv.ParseInt(line, 10, 64)
		seek_points[word] = num
	}

	// open file

	f, err := os.Open("search/Sorted_Index.txt")

	defer f.Close()
	if err != nil {
		log.Fatal(err)
	}

	page_rank_file, prerr := os.Open("search/page_ranks.txt")
	if prerr != nil {
		log.Fatal(prerr)
	}
	defer page_rank_file.Close()

	var page_ranks map[int]float64 = make(map[int]float64)
	page_rank_scanner := bufio.NewScanner(page_rank_file)
	for page_rank_scanner.Scan() {
		var line string = page_rank_scanner.Text()
		if line == "" {
			break
		}
		doc_id, _ := strconv.ParseInt(line[:strings.Index(line, ",")], 10, 64)
		line = line[strings.Index(line, ",")+1:]
		rank, _ := strconv.ParseFloat(line, 64)
		page_ranks[int(doc_id)] = rank
	}

	inlink_file, inerr := os.Open("search/in_links.txt")
	if inerr != nil {
		log.Fatal(inerr)
	}
	defer inlink_file.Close()

	var in_links map[int][]int = make(map[int][]int)
	inlink_scanner := bufio.NewScanner(inlink_file)
	for inlink_scanner.Scan() {
		var line string = inlink_scanner.Text()
		if line == "" {
			break
		}
		doc_id, _ := strconv.ParseInt(line[:strings.Index(line, ";")], 10, 64)
		line = line[strings.Index(line, ";")+1:]
		links := strings.Split(line, ",")
		parsed_links := make([]int, 0)
		for _, link := range links {
			if link == "" {
				continue
			}
			P_link, _ := strconv.ParseInt(link, 10, 64)
			parsed_links = append(parsed_links, int(P_link))
		}
		in_links[int(doc_id)] = parsed_links
	}

	outlink_file, ouerr := os.Open("search/out_links.txt")
	if ouerr != nil {
		log.Fatal(ouerr)
	}
	defer outlink_file.Close()

	var out_links map[int][]int = make(map[int][]int)
	outlink_scanner := bufio.NewScanner(outlink_file)
	for outlink_scanner.Scan() {
		var line string = outlink_scanner.Text()
		if line == "" {
			break
		}
		doc_id, _ := strconv.ParseInt(line[:strings.Index(line, ";")], 10, 64)
		line = line[strings.Index(line, ";")+1:]
		links := strings.Split(line, ",")
		parsed_links := make([]int, 0)
		for _, link := range links {
			if link == "" {
				continue
			}
			P_link, _ := strconv.ParseInt(link, 10, 64)
			parsed_links = append(parsed_links, int(P_link))
		}
		out_links[int(doc_id)] = parsed_links
	}

	var userSearch string

	for {
		if input == "" {
			fmt.Println("Enter the search query")

			scanner := bufio.NewScanner(os.Stdin)
			scanner.Scan()
			err = scanner.Err()
			if err != nil {
				log.Fatal(err)
			}
			userSearch = scanner.Text()
		} else {
			userSearch = input
		}

		var twoGrams []string
		var threeGrams []string

		var s = time.Now()

		var searchStrings []string = strings.Split(strings.ToLower(userSearch), " ")
		var unmodifiedStrings []string = searchStrings[:]

		for i := 0; i < len(searchStrings)-1; i++ {
			var gram []string = searchStrings[i : i+2]
			var newString string = strings.Join(gram, " ")
			twoGrams = append(twoGrams, newString)
		}
		for i := 0; i < len(searchStrings)-2; i++ {
			var gram []string = searchStrings[i : i+3]
			var newString string = strings.Join(gram, " ")
			threeGrams = append(threeGrams, newString)
		}

		searchStrings = append(searchStrings, twoGrams...)
		searchStrings = append(searchStrings, threeGrams...)

		var query_frequency map[string]int = make(map[string]int)

		for i := 0; i < len(searchStrings); i++ {
			if _, ok := query_frequency[searchStrings[i]]; ok {
				query_frequency[searchStrings[i]] += 1
			} else {
				query_frequency[searchStrings[i]] = 1
			}
		}

		var search_tokens map[string]Token = make(map[string]Token)

		for key := range query_frequency {
			ngram := strings.Count(key, " ")
			if ngram == 0 {
				search_tokens[key] = getTokenFromIndex(f, seek_points[key], key, 1)
			} else if ngram == 1 {
				search_tokens[key] = getTokenFromIndex(f, seek_points[key], key, 1.1)
			} else if ngram == 2 {
				search_tokens[key] = getTokenFromIndex(f, seek_points[key], key, 1.25)
			}
			word := []rune(key)
			stem := porterstemmer.StemWithoutLowerCasing(word)
			sstem := string(stem)
			if sstem != key {
				if ngram == 0 {
					search_tokens[sstem] = getTokenFromIndex(f, seek_points[sstem], sstem, 0.5)
				} else if ngram == 1 {
					search_tokens[sstem] = getTokenFromIndex(f, seek_points[sstem], sstem, 0.6)
				} else if ngram == 2 {
					search_tokens[sstem] = getTokenFromIndex(f, seek_points[sstem], sstem, 0.75)
				}
				searchStrings = append(searchStrings, sstem)
			}
		}

		var docTermCounts map[int]float64 = make(map[int]float64)

		for i := 0; i < len(searchStrings); i++ {
			for doc_id, _ := range search_tokens[searchStrings[i]].postings {
				if _, exists := docTermCounts[doc_id]; !exists {
					docTermCounts[doc_id] = 0
				}
				docTermCounts[doc_id]++
			}
		}

		fmt.Printf("after setup execution time %s\n", time.Since(s))
		topDocsRound1, _ := getNTopDocuments(docTermCounts, 1000)
		fmt.Printf("after round 1 execution time %s\n", time.Since(s))

		var scores map[int]float64 = make(map[int]float64)
		var length map[int]int = make(map[int]int)
		for key, val := range query_frequency {
			var term_token Token = search_tokens[key]
			var term_idf float64 = term_token.idf * math.Log(float64(val+1))
			for docID, _ := range topDocsRound1 {
				var tf float64 = term_token.postings[docID].tf
				if _, ok := scores[int(docID)]; ok {
					scores[docID] += term_idf * tf
				} else {
					scores[docID] = term_idf * tf
				}
				length[docID]++
			}
		}

		for docID, _ := range scores {
			query_words := docTermCounts[docID]
			if query_words > 0 {
				scores[docID] = scores[docID] / float64(length[docID])
				scores[docID] += math.Log(float64(query_words))
			} else {
				scores[docID] = scores[docID] / float64(length[docID])
			}
			scores[docID] = math.Log(scores[docID] + 1)
		}

		_, topDocsRound2 := getNTopDocuments(scores, 500)

		fmt.Printf("after round 2 execution time %s\n", time.Since(s))

		type strint_pair struct {
			str   string
			i     int
			score int
		}

		for docID, _ := range topDocsRound2 {

			termPositions := make([]strint_pair, 0)
			for term, _ := range query_frequency {
				for _, instance := range search_tokens[term].postings[docID].instances {
					termPositions = append(termPositions, strint_pair{str: term, i: int(instance.position), score: int(instance.styleScore)})
				}
			}

			sort.Slice(termPositions, func(i, j int) bool { return termPositions[i].i < termPositions[j].i })

			var current_block deque.Deque[strint_pair]

			start_index := 0
			end_index := math.MaxInt64

			window := math.MaxFloat64
			window_contains := 0
			var window_block []strint_pair

			var term_check map[string]int = make(map[string]int)

			for idx, term := range termPositions {
				if idx == 0 {
					start_index = term.i
				} else {
					end_index = term.i
				}
				current_block.PushBack(term)
				term_check[term.str]++
				for {
					if term_check[term.str] <= query_frequency[term.str] {
						break
					}
					popped := current_block.PopFront()
					start_index = current_block.Front().i
					term_check[popped.str]--
				}
				if current_block.Len() >= window_contains {
					if current_block.Len() > window_contains {
						window = math.MaxFloat64
					}
					if float64(end_index-start_index+1) < window {
						window = float64(end_index - start_index + 1)
						window_contains = current_block.Len()
						window_block = make([]strint_pair, 0)
						for i := 0; i < current_block.Len(); i++ {
							window_block = append(window_block, current_block.At(i))
						}
					}
				}
			}

			unmodified_term_indices := make(map[string]int, len(unmodifiedStrings))
			for i, term := range unmodifiedStrings {
				unmodified_term_indices[term] = i
			}
			lastIndex := -1
			differences := 0
			for _, pair := range window_block {
				index, found := unmodified_term_indices[pair.str]
				if !found {
					continue
				}
				if index < lastIndex {
					differences++
				}
				lastIndex = index
			}
			totalPairs := len(window_block)
			if totalPairs == 0 {
				scores[docID] = 0
				continue
			}
			style := 0.0
			min_style := math.MaxInt64
			max_style := math.MinInt64

			for _, pair := range window_block {
				style += float64(pair.score)
				if pair.score < min_style {
					min_style = pair.score
				}
				if pair.score > max_style {
					max_style = pair.score
				}
			}
			penalty := 1 - (float64(max_style-min_style) / 10)
			penalty = penalty * penalty
			style = ((style / float64(len(window_block))) / 50)
			style_score := (style * penalty) + 1
			// fmt.Println("Window Block:")
			// fmt.Println(window_block)
			// fmt.Printf("%d, Style: %f , Range: %d, Scores before: %f, ", docID, style, max_style-min_style, scores[docID])

			orderAccuracy := 1.0 - float64(differences)/float64(totalPairs)
			// fmt.Printf("window: %f ", window)
			if float64(len(unmodified_term_indices))/window > 1 {
				window = window / float64(len(unmodified_term_indices)) / 2
			} else {
				window = float64(len(unmodified_term_indices)) / window
			}

			// fmt.Printf("No log Window: %f, mult1: %f, mult2: %f, ", window, float64(len(searchStrings))/float64(len(window_block)), float64(len(window_block))/float64(len(searchStrings)))
			window = math.Log(window + 1)

			// fmt.Printf("Window: %f, Order: %f, Style: %f\n", window, orderAccuracy, style_score)

			scores[docID] *= window
			scores[docID] *= orderAccuracy
			scores[docID] *= style_score
			scores[docID] += page_ranks[docID]
		}

		topDocsRound3, _ := getNTopDocuments(scores, 100)

		fmt.Printf("after round 3 execution time %s\n", time.Since(s))

		hubScores := make(map[int]float64)
		authScores := make(map[int]float64)

		for node := range topDocsRound3 {
			hubScores[node] = 1.0
			authScores[node] = 1.0
		}

		for i := 0; i < 5; i++ {

			// Authority update
			newAuthScores := make(map[int]float64)
			for node, in_Links := range in_links {
				newAuthScore := 0.0
				for _, inLink := range in_Links {
					newAuthScore += hubScores[inLink]
				}
				newAuthScores[node] = newAuthScore
			}

			authNorm := 0.0
			for _, score := range newAuthScores {
				authNorm += score
			}
			authNorm = math.Sqrt(authNorm)

			for node := range newAuthScores {
				newAuthScores[node] /= authNorm
			}

			// Hub update
			newHubScores := make(map[int]float64)
			for node, out_Links := range out_links {
				newHubScore := 0.0
				for _, outLink := range out_Links {
					newHubScore += newAuthScores[outLink]
				}
				newHubScores[node] = newHubScore
			}

			hubNorm := 0.0
			for _, score := range newHubScores {
				hubNorm += score
			}
			hubNorm = math.Sqrt(hubNorm)

			for node := range newHubScores {
				newHubScores[node] /= hubNorm
			}
			// Update scores for the next iteration
			authScores = newAuthScores
			hubScores = newHubScores
		}

		for docID := range topDocsRound3 {
			scores[docID] += (math.Log(math.Log(authScores[docID]+hubScores[docID]+1)+1) * 0.1)
		}

		fmt.Printf("execution time %s\n", time.Since(s))

		keys := make([]int, 0, len(topDocsRound3))
		for k := range topDocsRound3 {
			keys = append(keys, k)
		}
		sort.Slice(keys, func(i, j int) bool { return scores[keys[i]] > scores[keys[j]] })

		// fmt.Println("scores:")
		// for _, key := range keys {
		// 	fmt.Printf("%d, %f", key, scores[key])
		// 	fmt.Printf(", %d\t", length[key])
		// }
		// fmt.Println("\n")

		for i := 0; i < 10 && i < len(keys); i++ {
			fmt.Printf("DocID: %d   ", keys[i])
			fmt.Println(jdata[strconv.Itoa(int(keys[i]))])
		}
	}
}

func main() {
	search("")
}
