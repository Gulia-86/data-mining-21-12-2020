import scrapy
import pymongo
import re

class AutoyoulaSpider(scrapy.Spider):
    name = "autoyoula"
    allowed_domains = ["auto.youla.ru"]
    start_urls = ["https://auto.youla.ru/"]
    db = None

    css_query = {
        "brands": "div.TransportMainFilters_block__3etab a.blackLink",
        "pagination": "div.Paginator_block__2XAPy a.Paginator_button__u1e7D",
        "ads": "article.SerpSnippet_snippet__3O1t2 a.blackLink",
    }

    data_query = {
        "title": lambda resp: resp.css("div.AdvertCard_advertTitle__1S1Ak::text").get(), #Название объявления
        "price": lambda resp: float(resp.css('div.AdvertCard_price__3dDCr::text').get().replace("\u2009", '')),
        "image_urls": lambda resp: resp.css('div.FullscreenGallery_snippet__1hAXU::attr(style)').re('(https?://[^\s]+)\)'), #Список фото объявления (ссылки)
        'specifications': lambda resp: resp.css("div.AdvertSpecs_row__ljPcX::text").get(), #Список характеристик
        'describe': lambda resp: resp.css("div.AdvertCard_descriptionWrap__17EU3 div.AdvertCard_descriptionInner__KnuRi::text").get(),#Описание объявления
        'author': lambda resp: AutoyoulaSpider.get_author(resp), #ссылка на автора объявления
    }
    @staticmethod
    def get_author(resp):
        script = resp.css('script:contains("window.transitState = decodeURIComponent")::text').get()
        re_str = re.compile(r"youlaId%22%2C%22([0-9|a-zA-Z]+)%22%2C%22avatar")
        result = re.findall(re_str, script)
        return f'https://youla.ru/user/{result[0]}' if result else None

    def __init__(self):
        self.db = pymongo.MongoClient('mongodb://localhost:27017')['gb_parse_youla']

    def save(self, data):
        collection = self.db['youla']
        collection.insert_one(data)

    def parse(self, response, **kwargs):
        brands_links = response.css(self.css_query["brands"])
        yield from self.gen_task(response, brands_links, self.brand_parse)

    def brand_parse(self, response):
        pagination_links = response.css(self.css_query["pagination"])
        yield from self.gen_task(response, pagination_links, self.brand_parse)
        ads_links = response.css(self.css_query["ads"])
        yield from self.gen_task(response, ads_links, self.ads_parse)

    def ads_parse(self, response):
        data = {}
        for key, selector in self.data_query.items():
            try:
                data[key] = selector(response)
            except (ValueError, AttributeError):
                continue
        if self.db != None:
            self.save(data)



    @staticmethod
    def gen_task(response, link_list, callback):
        for link in link_list:
            yield response.follow(link.attrib["href"], callback=callback)
