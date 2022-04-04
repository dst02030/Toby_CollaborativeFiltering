import urllib3
from BeautifulSoup4 import *
from urlparse import urljoin
from pysqlite2 import dbapi2 as sqlite




class crawler:
    # Initialize the crawler with the name of database
    def __init__(self, dbname):
        self.con = sqlite.connect(dbname)

    def __del__(self):
        self.con.close()

    def dbcommit(self):
        self.con.commit()

    

    # Auxilliary function for getting an entry id and adding
    # it if it's not present
    def getentryid(self, table, field, value, createnew = True):
        cur = self.con.execute(
            f"select rowid from {table} where {field} = {value}")

        res = cur.fetchone()

        if res == None:
            cur = self.con.execute(
                f"insert into {table} ({field}) values ({value})")
            return cur.lastrowid

        else:
            return res[0]

    # Index an individual page
    def addtoindex(self, url, soup):
        if self.isindexed(url): return
        print("Indexing " + url)


        # Get the individual words
        text = self.gettextonly(soup)
        words = self.separatewords(text)

        # Get the URL id
        urlid = self.getentryid('urllist', 'url', url)

        # Link each word to this url
        for i in range(len(words)):
            word = words[i]
            if word in ignorewords: continue

            wordid = self.getentryid('wordlist', 'word', word)
            self.con.execute(f'''insert into wordlocation(urlid, wordid, location)\
            values ({urlid}, {wordid}, {i})''')
                             

    # Extract the text from an HTML page (no tags)
    def gettextonly(self, soup):
        v = soup.string

        if v == None:
            c = soup.contents
            resulttext = ''

            for t in c:
                subtext = self.gettextonly(t)
                resulttext += subtext + '\n'

            return resulttext

        else:
            return v.strip()

    # Separate the words by any non-whitespace character
    def separatewords(self, text):
        splitter = re.compile('\\W*')
        return [s.lower() for s in splitter.split(text) if s!= '']

    # Return true if this url is already indexed
    def isindexed(self, url):
        u = self.con.execute(
            f"select rowid from urllist where url = {url}").fetchone()

        if u != None:
            # Check if it has actually been crawled
            v = self.con.execute(
                f"select * from wordlocation where urlid = {u[0]}").fetchone()

            if v!= None: return True
        return False

    # Add a link between two pages
    def addlinkref(self, urlFrom, urlTo, linkText):
        pass

    # Starting with a list of pages, do a breadth
    # first search to the given depth, indexing pages
    # as we go
    def crawl(self, pages, depth = 2):
        for i in range(depth):
            newpages = set()

            for page in pages:
                try:
                    c = urllib3.urlopen(page)

                except:
                    print(f"Could not open {page}")
                    continue

                soup = BeautifulSoup(c.read())
                self.addtoindex(page, soup)

                links = soup('a')

                for link in links:
                    if 'href' in dict(link.attrs):
                        url = urljoin(page, link['href'])
                        if url.find("'") != -1: continue

                        url = url.split('#')[0] # Remove location portion

                        if url[:4] == 'http' and not self.isindexed(url):
                            newpages.add(url)

                        linkText = self.gettextonly(link)
                        self.addlinkref(page, url, linkText)


                self.dbcommit()

            pages = newpages

    # Create the database tables
    def createindextables(self):
        self.con.execute('create table urllist(url)')
        self.con.execute('create table wordlist(word)')
        self.con.execute('create table wordlocation(urlid, wordid, location)')
        self.con.execute('create table link(fromid integer, toid integer)')
        self.con.execute('create table linkwords(wordid, linkid)')
        self.con.execute('create index wordidx on wordlist(word)')
        self.con.execute('create index urlidx on urllist(url)')
        self.con.execute('create index wordurlidx on wordlocation(wordid)')
        self.con.execute('create index urltoidx on link(toid)')
        self.con.execute('create index urlfromidx on urlfromidx(fromid)')
        self.dbcommit()
        

    def calculatepagerank(self, iterations = 20):
        # Clear out the current PageRank tables
        self.con.execute('drop table if exists pagerank')
        self.con.execute('create table pagerank(urlid primary key, score)')

        # Initialize every url with a PageRank of 1
        self.con.execute('insert into pagerank select rowid, 1.0 from urllist')
        self.dbcommit()

        for i in range(iterations):
            print("Iteration %d" % (i))
            for (urlid, ) in self.con.execute('select rowid from urllist'):
                pr = .15

                # Loop through all the pages that link to this one
                for (linker, ) in self.con.execute("SELECT distinct fromid from link where toid = %d" % urlid):
                    # Get the PageRank of the linker
                    linkingpr = self.con.execute("SELECT score from pagerank where urlid = %d" % linker).fetchone()[0]


                    # Get the total number of links from the linker
                    linkingcount = self.con.execute("SELECT count(*) from link where fromid = %d" % linker).fetchone()[0]
                    pr += .85 * (linkingpr / linkingcount)

                self.con.execute("UPDATE pagerank set score = %f where urlid = %d" % (pr, urlid))
            self.dbcommit()

    def pagerankscore(self, rows):
        pageranks = dict([(row[0], self.con.execute("SELECT socre FROM pagerank WHERE urlid = %d" % row[0]).fetchone()[0]) for row in rows])
        maxranks = max(pageranks.values())
        normalizedscores = dict([(u, float(l)/maxrank) for (u, l) in pageranks.items()])
        return normalizedscores


# New class that you'll use for searching
class searcher:
    def __init__(self, dbname):
        self.con = sqlite.connect(dbname)

    def __del__(self):
        self.con.close()
    
    def getmatchrows(self, q):
        # Strings to build the query
        fieldlist = 'w0.urlid'
        tablelist = ''
        clauselist = ''
        wordids = []


        # Split the words by spaces
        words = q.split(' ')
        tablenumber = 0


        for word in words:
            # Get the word ID
            wordrows = self.con.execute(
                f"select rowid from wordlist where word = {word}").fetchone()

            if wordrow != None:
                wordid = wordrow[0]
                wordids.append(wordid)

                if tablenumber > 0:
                    tablelist += ','
                    clauselist += ' and '
                    clauselist += 'w%d.urlid=w%d.urlid and ' % (tablenumber-1, tablenumber)

                filedlist += ', w%d.location' % tablenumber
                tablelist += f'wordlocation w{tablenumber}'
                clauselist += 'w{tablenumber}={wordid}'
                tablenumber += 1

        # Create the query from the separate parts
        fullquery = f"select {fieldlist} from {tablelist} where {clauselist}"
        cur = self.con.execute(fullquery)
        rows = [row for row in cur]


        return rows, wordids


    def getcoredlist(self, rows, wordids):
        totalscores = dict([(row[0], 0) for row in rows])

        # This is where you'll later put the scoring functions
        weights = []

        for (weight, socres) in weights:
            for url in totalscores:
                totalscores[url] += weight * scores[url]

        return totalscores


    def geturlname(self, id):
        return self.con.execute(
            "select url from urllist where rowid=%d" % id).fetchone()[0]

    def query(self, q):
        rows, wordids = self.getmatchrows(q)
        scores = self.getscoredlist(rows, wordids)
        rankedscores = sorted([(score, url) for (url, score) in scores.items()], reverse = 1)

        for (score, urlid) in rankedscores[:10]:
            print("%f\t%s" % (score, self.geturlname(urlid)))
    

    def normalizescores(self, scores, smallIsBetter=0):
        vsmall = 0.00001 # Avoid division by zero errors
        if smallIsBetter:
            minscore = min(scores.values())
            return dict([(u, float(minscore)/max(vsmall, l)) for (u, l) in scores.items()])

        else:
            maxscore = max(scores.values())
            if maxscore == 0: maxscore = vsmall
            return dict([(u, float(c)/maxscore) for (u, c) in scores.items()])

    def frequencyscore(self, rows):
        count = dict([(row[0], 0) for row in rows])
        for row in rows: counts[row[0]]+=1
        return self.normalizescores(counts)

    def locationsocre(self, rows):
        locations = dict([(row[0], 1000000) for row in rows])
        for row in rows:
            loc = sum(row[1:])
            if loc<locations[row[0]]: locations[row[0]] = loc

        return self.normalizescores(locations, smallIsBetter = 1)


    def distancesocre(self, rows):
        # If there's only one word, everyone wins!
        if len(rows[0])<2: return dict([(row[0], 1.0) for row in rows])

        # Initialize the dictionary with large values
        mindistance = dict([(row[0], 1000000) for row in rows])

        for row in rows:
            dist = sum([abs(row[i] - row[i-1]) for i in range(2, len(row))])
            if dist<mindistance[row[0]]: mindistance[row[0]] = dist

        return self.normalizescores(mindistance, smallIsBetter = 1 )

    
    def inboundlinksocre(self, rows):
        uniqueurls = set([row[0] for row in rows])
        inboundcount = dict([(u, self.con.execute('SELECT count(*) FROM link WHERE toid = %d' % u).fetchone()[0]) for u in uniqueurls])
        return self.normalizescores(inboundcount)


    def linktextscore(self, rows, wordids):
        linkscores = dict([(row[0], 0) for row in rows])

        for wordid in wordids:
            cur = self.con.execute("SELECT link.fromid, link.toid from linkwords, link where wordid = %d and linkwords.linkid = link.rowid" % wordid)

            for (fromid, toid) in cur:
                if toid in linkscores:
                    pr = self.con.execute("SELECT score FROM pagerank WHERE urlid = %d" % fromid).fetchone()[0]
                    linkscores[toid] += pr

        maxscore = max(linkscores.values())
        normalizedscores = dict([(u, float(l)/maxscore) for (u, l) in linkscores.items()])
        return normalizedscores
        

# Create a list of words to ignore
ignorewords = set(['the', 'of', 'to', 'and', 'a', 'in', 'is', 'it'])
