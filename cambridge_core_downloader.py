import requests
from bs4 import BeautifulSoup


class CambridgeCoreBook:
    doi = ""
    title = ""
    author = ""
    chapters = []
    html = ""

    def __init__(self, doi):
        self.doi = doi
        self.get_html()
        self.get_title()
        self.get_author()
        self.get_chapters()

    def get_html(self):
        doi_url = " https://doi.org/" + self.doi
        try:
            response = requests.get(doi_url)
        except not response.status_code == 200:
            raise
        self.html = BeautifulSoup(response.text, 'html.parser')

    def get_chapters(self):
        self.chapters = self.html.find_all("ul", class_="details")

    def get_author(self):
        self.author = self.html.find("meta", {"name": "citation_author"})["content"]

    def get_title(self):
        self.title = self.html.find("meta", {"name": "citation_title"})["content"]


if __name__ == "__main__":
    print("Welcome to Cambridge Core Book Downloader!")
    book = CambridgeCoreBook("10.1017/9781108923859")
    print(f"Downloading \"{book.title}\" by {book.author}")
