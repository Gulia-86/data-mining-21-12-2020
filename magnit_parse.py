import requests
import bs4
from urllib.parse import urljoin
import pymongo
import re
from datetime import datetime, date

class MagnitParse:
    def __init__(self, start_url, mongo_db):
        self.start_url = start_url
        self.db = mongo_db

    def __get_soup(self, url) -> bs4.BeautifulSoup:
        # todo предусмотреть внештатные ситуации
        response = requests.get(url)
        return bs4.BeautifulSoup(response.text, 'lxml')

    def run(self):
        for product in self.parse():
            self.save(product)

    def parse(self):
        soup = self.__get_soup(self.start_url)
        catalog_main = soup.find('div', attrs={'class': 'сatalogue__main'})
        for product_tag in catalog_main.find_all('a', recursive=False):
            try:
                yield self.product_parse(product_tag)
            except AttributeError:
                pass

    def create_date(self, arg, arg2):
        date_str = arg.find("div", attrs={"class": "card-sale__date"}).text
        res = str(re.findall(r'\d+\s[а-яА-я]+', date_str)[arg2])
        MONTHS = {
            "янв": 1,
            "фев": 2,
            "мар": 3,
            "апр": 4,
            "май": 5,
            "мая": 5,
            "июн": 6,
            "июл": 7,
            "авг": 8,
            "сен": 9,
            "окт": 10,
            "ноя": 11,
            "дек": 12,
        }
        res = datetime(
            year=datetime.now().year,
            day=int(str(re.findall(r'\d+', res)[0])),
            month=MONTHS[res[3:6]],
        )
        return res

    def product_parse(self, product: bs4.Tag) -> dict:
        product = {
            'url': urljoin(self.start_url, product.get('href')),
            'promo_name': product.find(class_='card-sale__header').text,
            'product_name': product.find(class_='card-sale__title').text,
            'old_price':  float(".".join(product.find("div", attrs={"class": "label__price label__price_old"}).text.split())),
            'new_price': float(".".join(product.find("div", attrs={"class": "label__price label__price_new"}).text.split())),
            'image_url': urljoin(self.start_url, product.find('img').get('data-src')),
            'date_from': self.create_date(product, 0),
            'date_to': self.create_date(product, 1),
        }
        return product



    def save(self, data):
        collection = self.db['magnit']
        collection.insert_one(data)
        print(1)


if __name__ == '__main__':
    database = pymongo.MongoClient('mongodb://localhost:27017')['gb_parse_12']
    parser = MagnitParse("https://magnit.ru/promo/?geo=moskva", database)
    parser.run()