import time
import json
from urllib.parse import quote
from datetime import timedelta
from multiprocessing.dummy import Pool
from curl_cffi import requests
from bs4 import BeautifulSoup


class Pooler:
    def __init__(self, threads):
        self.threads = threads
        self.awaiting_processes = []
        self.pool = Pool(threads)
    
    def add(self, func, *args, **kwargs):
        self.awaiting_processes.append((func, args, kwargs))
    
    def run(self, concurrent=True, callback=True, eta=True, minimum_percentage_diff=0.1):
        prc_count = len(self.awaiting_processes)
        unfinished_prc = object()
        start_time = time.time()
        last_percentage = 0
        minimum_percentage_diff = minimum_percentage_diff / 100
        self.results = [unfinished_prc] * prc_count
        
        def order_decorator(func, order):
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                self.results[order] = result
                return result
            return wrapper
        
        def process_callback(x):
            if concurrent and self.awaiting_processes:
                try:
                    prc = self.awaiting_processes.pop(0)
                    self.pool.apply_async(
                        order_decorator(prc[0], prc_count - (len(self.awaiting_processes) + 1)),
                        *prc[1:],
                        callback=process_callback,
                        error_callback=process_callback)
                except Exception:
                    pass
        
        while unfinished_prc in self.results:
            if self.awaiting_processes:
                for _ in range(self.threads if len(self.awaiting_processes) > self.threads else len(self.awaiting_processes)):
                    prc = self.awaiting_processes.pop(0)
                    self.pool.apply_async(
                        order_decorator(prc[0], prc_count - (len(self.awaiting_processes) + 1)),
                        *prc[1:],
                        callback=process_callback,
                        error_callback=process_callback)
            
            if concurrent:
                unfinished_prc_count = self.results.count(unfinished_prc)
                
                while unfinished_prc in self.results:
                    time.sleep(0.05)
                    
                    if callback and self.results.count(unfinished_prc) != unfinished_prc_count:
                        unfinished_prc_count = self.results.count(unfinished_prc)
                        finished_prc_count = prc_count - unfinished_prc_count
                        
                        if (finished_prc_count / prc_count) - last_percentage <= minimum_percentage_diff:
                            continue
                        
                        if eta:
                            time_elapsed = time.time() - start_time
                            time_total = (time_elapsed / finished_prc_count) * prc_count
                            time_left = str(timedelta(seconds=time_total - time_elapsed))[:-3]
                        
                        last_percentage = finished_prc_count / prc_count
                        
                        print(f'Phase {finished_prc_count // self.threads}: [' +
                        ('#' * int(20 * (finished_prc_count / prc_count))).ljust(20, ' ') +
                        '] ' +
                        f'{last_percentage:.2%}' +
                        f' ETA: {time_left}' if eta else '')
            else:
                while self.results.count(unfinished_prc) != len(self.awaiting_processes):
                    time.sleep(0.05)
                
                unfinished_prc_count = self.results.count(unfinished_prc)
                finished_prc_count = prc_count - unfinished_prc_count
                
                if callback and (finished_prc_count / prc_count) - last_percentage >= minimum_percentage_diff:
                    if eta:
                        time_elapsed = time.time() - start_time
                        time_total = (time_elapsed / finished_prc_count) * prc_count
                        time_left = str(timedelta(seconds=time_total - time_elapsed))[:-3]
                    
                    last_percentage = finished_prc_count / prc_count
                    
                    print(f'Phase {finished_prc_count // self.threads}: [' +
                    ('#' * int(20 * (finished_prc_count / prc_count))).ljust(20, ' ') +
                    '] ' +
                    f'{last_percentage:.2%}' +
                    f' ETA: {time_left}' if eta else '')
        
        return self.results


class Tureng:
    def __init__(self):
        self.session = requests.Session(headers={
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'tr-TR,tr;q=0.9',
            'cache-control': 'no-cache',
            'dnt': '1',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://tureng.com/tr/turkce-ingilizce',
            'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        }, timeout=10, impersonate='chrome')
        self.souper = lambda x: BeautifulSoup(x, 'lxml')
        #self.part_of_speeches = {}
        #self.categories = {}
    
    def get_translations(self, word):
        while True:
            try:
                soup = self.souper(self.session.get('https://tureng.com/tr/turkce-ingilizce/' + quote(word)).text)
                
                # 4 farklı çeviri türü var, ing/türkçe, türkçe/ing ve aranan kelimenin başka kelimeler ile yine ing/türkçe, türkçe/ing çevirileri
                # bu çevirileri anlamanın yolu, baştaki h2'nin içinde "diğer terimlerle kazandığı" olup olmaması, yani bu yazıyorsa başka kelimeler ile çeviri demektir
                # çevirinin ing/türkçe, türkçe/ing mi olduğunu anlamak için ise tablonun en üstündeki "Kategori" ardından gelen dile bakılır, önce ing geliyorsa ing/türkçe, türkçe geliyorsa türkçe/ing
                translations = {
                    'ing/tur': [],
                    'tur/ing': [],
                    'alt ing/tur': [],
                    'alt tur/ing': []
                }
                
                for h2 in soup.select('h2'):
                    table = h2.find_next('table')
                    
                    if not table:
                        break
                    
                    ing_to_tur = table.select_one('th[class="c2"]').getText() == 'İngilizce'
                    
                    for tr in table.select('tr[class^="tureng-manual"]:not([class*="example-sentences-row"])'):
                        en_word = tr.select_one('td[class="en tm"]')
                        tr_word = tr.select_one('td[class="tr ts"]')
                        category = tr.select_one('td[class="hidden-xs"]').getText()
                        part_of_speech = None
                        
                        #if category and category not in self.categories:
                        #    self.categories.update({
                        #        category: len(self.categories)
                        #    })
                        
                        if i := en_word.select_one('i'):
                            part_of_speech = ii if (ii := i.getText()) else None # there are empty <i> elements sometimes
                        
                        #if part_of_speech and part_of_speech not in self.part_of_speeches:
                        #    self.part_of_speeches.update({
                        #        part_of_speech: len(self.part_of_speeches)
                        #    })
                        
                        en_word = en_word.select_one('a').getText().strip()
                        tr_word = tr_word.getText().strip()
                        #category = self.categories[category]
                        #part_of_speech = self.part_of_speeches[part_of_speech]
                        
                        if 'diğer terimlerle kazandığı' in h2.getText():
                            if ing_to_tur:
                                translations['alt ing/tur'].append((en_word, tr_word, category, part_of_speech))
                            else:
                                translations['alt tur/ing'].append((en_word, tr_word, category, part_of_speech))
                        
                        else:
                            if ing_to_tur:
                                translations['ing/tur'].append((en_word, tr_word, category, part_of_speech))
                            else:
                                translations['tur/ing'].append((en_word, tr_word, category, part_of_speech))
                
                return translations
        
            except Exception as e:
                print(e)
                time.sleep(1)
    
    def get_word_completions(self, query):
        while True:
            try:
                resp = self.session.get(f'https://ac.tureng.co/?t={quote("  " + query)}&l=entr')
                
                return {
                    'query': query,
                    'results': set(resp.json())
                }
            except Exception as e:
                print(e)
                time.sleep(1)
    
    def find_all_words_starting_with(self, query, threads=100):
        all_words = set()
        waiting_for_search = {query}
        last_searched_words = set()
        pool = Pooler(threads)
        characters = '0123456789abcçdefgğhıijklmnoöpqrsştuüvwxyz'
        
        while waiting_for_search:
            print(f'{len(all_words)}, {len(waiting_for_search)}')
            
            for query in waiting_for_search:
                pool.add(self.get_word_completions, query)
            
            results = pool.run(callback=None)
            new_waiting_for_search = set()
            
            for result in results:
                query = result['query']
                new_words = result['results']
                
                all_words.update(new_words)
                
                if len(new_words) == 10:
                    new_waiting_for_search.update(new_words.difference([query]))
                    new_waiting_for_search.update([query + x for x in characters])
                    new_waiting_for_search.update([query + ' ' + x for x in characters])
            
            # c-ç, ı-i, o-ö gibi harfler yer değiştirebiliyor, dolayısıyla eğer bu iki harf ile de kelime oluşturabilen prefix var ise
            # bot ölüm döngüsüne giriyor, "jantı" buna bir örnek, "jantı" diye aratınca "janti", "janti" diye aratınca "jantı" çıkıyor
            waiting_for_search = new_waiting_for_search.difference(last_searched_words)
            last_searched_words = {x['query'] for x in results}
        
        return list(all_words)
    
    def update_database(self, wordlist_path, database_path, completed_words_path, threads=100, max_word_limit=10_000):
        with open(wordlist_path) as fp:
            wordlist = set(json.load(fp))
        
        with open(database_path) as fp:
            database = json.load(fp)
        
        with open(completed_words_path) as fp:
            completed_words = set(json.load(fp))
        
        pool = Pooler(threads)
        
        while next_words := list(wordlist.difference(completed_words))[:max_word_limit]:
            completed_words.update(next_words)
            
            for word in next_words:
                pool.add(self.get_translations, word)
            
            for results in pool.run(minimum_percentage_diff=1):
                for translation in results['ing/tur']:
                    completed_words.update([translation[0]])
                    database['ing'].setdefault(translation[0], [])

                    if translation[1] not in database['ing'][translation[0]]:
                        database['ing'][translation[0]].append(translation[1])
                    
                    if translation[1] not in wordlist:
                        wordlist.update([translation[1]])
                
                for translation in results['tur/ing']:
                    completed_words.update([translation[1]])
                    database['tur'].setdefault(translation[1], [])

                    if translation[0] not in database['tur'][translation[1]]:
                        database['tur'][translation[1]].append(translation[0])
                    
                    if translation[0] not in wordlist:
                        wordlist.update([translation[0]])
                
                for translation in results['alt ing/tur']:
                    if translation[0] not in wordlist:
                        wordlist.update([translation[0]])
                    
                    if translation[1] not in wordlist:
                        wordlist.update([translation[1]])
                
                for translation in results['alt tur/ing']:
                    if translation[0] not in wordlist:
                        wordlist.update([translation[0]])
                    
                    if translation[1] not in wordlist:
                        wordlist.update([translation[1]])
            
            with open(wordlist_path, 'w') as fp:
                json.dump(list(wordlist), fp)
            
            with open(database_path, 'w') as fp:
                json.dump(database, fp)
            
            with open(completed_words_path, 'w') as fp:
                json.dump(list(completed_words), fp)
        
        # son kez sorted olarak kaydet
        with open(database_path, 'w') as fp:
            json.dump({
                k: dict(sorted(v.items(), key=lambda x: x[0]))
                for k, v in database.items()
            }, fp)