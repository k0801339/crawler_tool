import requests
from requests_html import HTML
from pprint import pprint

# from multiprocessing import Pool7
import re
import os

class SimpleParser():
    '''
    Basic parser parent class
    '''
    def __init__(self, start_url):
        # setting the parser
        #self.domain = "https://www.ptt.cc"
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
        self.domain = "https://www.ptt.cc"
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
        self.domain = "https://search.books.com.tw/"
    
    # def fetch(self, url): 
    # need not override it

    def parse_article_entries(self, doc):
        html = HTML(html=doc)
        post_entries = html.find("div.cntlisearch08 form ul.searchbook li.item")
        return post_entries

    def parse_article_meta(self, entry):
        meta = {
            'title': entry.find("h3 a[rel='mid_name']", first=True).text,
            # 可以以後修改為 author list，避免某些書籍有譯者or插畫家等問題
            'author': entry.find("a[rel='go_author']")[0].text,
            'publish': entry.find("a[rel='mid_publish']", first=True).text,
            #'date':  entry.text,
            'discount': entry.find("span.price strong b", first=True).text + "折",
            'price': entry.find("span.price strong b")[-1].text,
            'summary': entry.find("p", first=True).text,
            #'image': entry.find("a img.itemcov", first=True).attrs['src'],
            # 無法取得 img attrs src，改從data-original attr取得
            #'image': entry.find("a img"),
            'link': "https:" + entry.find("a[rel='mid_image']", first=True).attrs['href']

        }
        # author list: 處理當同時有作者、譯者、插畫家等複數創作者存在時
        author_list = entry.find("a[rel='go_author']")
        if len(author_list) > 1:
            for author in author_list[1:]:
                meta['author'] += ' ' + author.text

        # price list: 可能有不打折的情況
        if len(entry.find("span.price strong b")) < 2:
            meta['discount'] = "優惠價"

        # for data
        match_date = re.search("[0-9]{4}-[0-9]{2}-[0-9]{2}", entry.text)
        meta['date'] = match_date.group()

        # for image
        image_origin_link = entry.find("a img.itemcov", first=True).attrs['data-original']
        match_img = re.search("https://www.books.com.tw/img/.+&w", image_origin_link)
        if not match_img:
            meta['image'] = "暫無圖片~"
        # remove scaling
        else:
            meta['image'] = match_img.group()[:-2]

        return meta

    def entry_filter(self, entry, option={"type": "chinese-only"}):
        '''
        剔除部分不吻合之選項
        '''
        booktype = entry.find("span.cat", first=True).text
        if "type" in option and option['type'] == "chinese-only" and booktype != "中文書":
            return False
        
        if "author" in option:
            bookauthor = entry.find("a[rel='go_author']")
            valid = False
            if len(bookauthor) > 1:
                for author_i in bookauthor:
                    if option['author'] == author_i.text:
                        valid = True
                        break
            else:
                if option['author'] == bookauthor.text:
                    valid = True
            if not valid:
                return False

        if 'publish' in option and option['publish'] != entry.find("a[rel='mid_publish']", first=True).text:
            return False
        
        return True

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
    
    '''
    Command mode: 現在支援文字輸入搜尋了!
    '''
    start_url = "https://search.books.com.tw/search/query/cat/bka/key/[input]/sort/[seq]/"
    # 參考搜尋url： 找作者、依上市日期排列
    # start_url_date_author = "https://search.books.com.tw/search/query/key/東野圭吾/sort/5/adv_author/1"

    search_input = input("請輸入欲搜尋的關鍵字: ")
    while not search_input:
        search_input = input("請輸入欲搜尋的關鍵字: ")

    start_url = start_url.replace("[input]", search_input)
    print(start_url)

    # 進階搜尋欄位
    option = {"type": "chinese"}
    adv_filter = input("篩選欄位: 1. 作者 2. 出版社 3. 書名包括此關鍵字 (不輸入or錯誤輸入視為預設)  : ")
    if adv_filter == "1":
        start_url += "adv_author/1"
        option["author"] = search_input
    elif adv_filter == "2":
        start_url += "adv_pub/1"
        option["publish"] = search_input
    elif adv_filter == "3":
        start_url += "adv_title/1"

    # 排序
    adv_seq = input("排序: 1. 預設關聯度 2. 出版時間 3. 暢銷度 (不輸入or錯誤輸入視為預設選項->1)  : ")
    if adv_seq == "2":
        adv_seq = "5"
    elif adv_seq == "3":
        adv_seq = "9"
    else:
        adv_seq = "1"
    
    start_url = start_url.replace("[seq]", adv_seq)
    
    print(start_url)
    os.system("pause")

    '''
    預期功能: 
    可選擇查詢-> "書名(系列)" "作者" "出版社" 
    排序選項-> 出版時間(固定新的在前) 暢銷度(固定熱賣的在前)
    顯示-> 第一頁，視使用者是否要繼續搜尋
    模糊度-> 書名(使用博客來預設) 作者(作者欄位須有符合欲查找之目標方呈現)
    項目-> 暫時只允許 1. 圖書類 2. 中文書項目(排除外文、簡體)

    '''

    booksParser = BooksParser(start_url)
    numPages = 1

    metapage = booksParser.fetch(start_url)
    entries = booksParser.parse_article_entries(metapage.text)

    if not entries:
        print("\n找不到此關鍵字之資料!\n")

    print("------------------------------")
    for entry in entries:
        if not booksParser.entry_filter(entry, option=option):
            continue
        print()
        meta = booksParser.parse_article_meta(entry)
        print("{}\n{} {} {}\n{} {}\n{}\nLink: {}\nImage link: {}".format(meta['title'], meta['author'], meta['publish'], meta['date'], meta['discount'], meta['price']+'元', 
            meta['summary'], meta['link'], meta['image']))
        
        print()
        print("------------------------------")

    '''
    meta_data = pttParser.get_pages_meta(start_url, numPages)
    
    for meta in meta_data:
        padding = ' ' * (70-get_width(meta['title']))
        if meta['push'] == "爆":
            pattern = "{:<3}{:<}{}{:^7}{:>13}"
        else:
            pattern = "{:<4}{:<}{}{:^7}{:>13}"
        
        print(pattern.format(meta['push'], meta['title'], padding, meta['date'], meta['author'])) 
    '''

    