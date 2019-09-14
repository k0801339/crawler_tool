import requests
from requests_html import HTML
from pprint import pprint
import os

# from multiprocessing import Pool7
import re

class SimpleParser():
    '''
    Basic parser parent class
    '''
    def __init__(self, start_url):
        # setting the parser
        self.domain = "https://www.ptt.cc"
        self.start_url = start_url
    
    def fetch(self, url):
        '''
        fetch the htmltext of corresponding url, with specific crawling format if needed
        '''
        response = requests.get(url)
        return response

    def parse_article_entries(self, doc):
        '''
        fetch every entry of current page
        '''
        pass

    def parse_article_meta(self, entry):
        '''
        parse current entry then return its metadata
        '''
        pass

    def parse_nextlink(self, doc):
        '''
        parse next link by htmltext
        '''
        pass

    def get_pages_meta(self, url, numPages=5):
        '''
        Given # of pages, return all entries' metadata of all pages
        '''
        pass
    
    def get_metadata(self, url):
        '''
        parse the corresponding htmltext
        '''
        pass

class PTTParser(SimpleParser):
    '''
    PTT simple crawler
    '''
    def __init__(self, start_url):
        super().__init__(start_url)
        # self.domain = "https://www.ptt.cc"
        # self.start_url = start_url

    def fetch(self, url):
        response = requests.get(url)
        response = requests.get(url, cookies={'over18': '1'})
        return response

    def parse_article_entries(self, doc):
        html = HTML(html=doc)
        post_entries = html.find("div.r-ent")
        return post_entries

    def parse_article_meta(self, entry):
        '''
        Return specific information about each post entry
        '''
        
        meta = {
            'title': entry.find('div.title', first=True).text,
            'push': entry.find('div.nrec', first=True).text,
            'date': entry.find('div.date', first=True).text
        }

        try:
            meta['author'] = entry.find('div.author', first=True).text
            meta['link'] = entry.find('div.title a', first=True).attrs['href']
        except Exception:
            if '(本文已被刪除)' in meta['title']:
                # e.g., (本文已被刪除)[okok] -> okok: author
                match = re.search("\[(\w*)\]", meta['title'])
                if match:
                    meta['author'] = match.group(1)
            elif "(已被" in meta['title'] and "刪除)" in meta['title']:
                # e.g., "(已被admin刪除) <okok> op"
                match = re.search("<(\w*)>", meta['title'])
                if match:
                    meta['author'] = match.group(1)
            meta['link'] = "EMPTY"
        
        return meta

    def parse_nextlink(self, doc):
        html = HTML(html=doc)
        prev_page = html.find(".action-bar a.btn.wide")
        # second link
        nextlink = prev_page[1].attrs['href']
        return self.domain + nextlink

    # New function: can get multiple pages of PTT
    def get_metadata(self, url):

        resp = self.fetch(url)
        post_entries = self.parse_article_entries(resp.text)
        nextlink = self.parse_nextlink(resp.text)

        metadata = [self.parse_article_meta(post) for post in post_entries]
        return metadata, nextlink

    def get_pages_meta(self, url, numPages=5):
        collect_post = []
        nowlink = url

        for _ in range(numPages):
            postdata, nextlink = self.get_metadata(nowlink)
            collect_post += postdata
            nowlink = nextlink
        
        return collect_post

class BooksParser(SimpleParser):
    '''
    Simple parser for books.com.tw (博客來 web bookstore)
    '''
    def __init__(self, start_url):
        super().__init__(start_url)
    
    # def fetch(self, url): 
    # need not override it

    def parse_article_entries(self, doc):
        html = HTML(html=doc)
        post_entries = html.find("div.r-ent")
        return post_entries


# calculate Chinese sentenses' true length in python print function
widths = [
    (126,  1), (159,  0), (687,   1), (710,  0), (711,  1),
    (727,  0), (733,  1), (879,   0), (1154, 1), (1161, 0),
    (4347,  1), (4447,  2), (7467,  1), (7521, 0), (8369, 1),
    (8426,  0), (9000,  1), (9002,  2), (11021, 1), (12350, 2),
    (12351, 1), (12438, 2), (12442,  0), (19893, 2), (19967, 1),
    (55203, 2), (63743, 1), (64106,  2), (65039, 1), (65059, 0),
    (65131, 2), (65279, 1), (65376,  2), (65500, 1), (65510, 2),
    (120831, 1), (262141, 2), (1114109, 1),
]

def get_width(s):
    """Return the screen column width for unicode ordinal o."""
    global widths
    #print(s)
    def char_width(o):
        if o == 0xe or o == 0xf:
            return 0
        for num, wid in widths:
            #print(o, num)
            if o <= num:
                return wid
        return 1
    return sum(char_width(ord(c)) for c in s)
    

if __name__ == '__main__':
    
    start_url = "https://www.ptt.cc/bbs/NBA/index.html"

    pttParser = PTTParser(start_url)
    numPages = 1

    meta_data = pttParser.get_pages_meta(start_url, numPages)
    
    for meta in meta_data:
        padding = ' ' * (70-get_width(meta['title']))
        if meta['push'] == "爆":
            pattern = "{:<3}{:<}{}{:^7}{:>13}"
        else:
            pattern = "{:<4}{:<}{}{:^7}{:>13}"
        
        print(pattern.format(meta['push'], meta['title'], padding, meta['date'], meta['author'])) 

    