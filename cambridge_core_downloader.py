from pathlib import Path
import requests
from bs4 import BeautifulSoup


class CambridgeCoreBook:
    doi = ''
    title = ''
    author = ''
    chapters = []
    html = ''
    base_url = 'https://www.cambridge.org'
    output_dir = ''

    def __init__(self, doi):
        self.doi = doi
        self.get_html()
        self.get_title()
        self.get_author()
        self.make_output_dir()
        self.get_chapters()
        print(f'Found book "{self.title}" by {self.author}.')

    def get_html(self):
        doi_url = 'https://doi.org/' + self.doi
        try:
            response = requests.get(doi_url)
        except not response.status_code == 200:
            raise
        self.html = BeautifulSoup(response.text, 'html.parser')

    def get_chapters(self):
        all_chapters_html = self.html.find_all('ul', class_='details')
        for single_chapter_html in all_chapters_html:
            chapter_dict = {'title': (single_chapter_html.find_all('li')[0].get_text().strip().split('\n'))[0],
                            'pages': (single_chapter_html.find_all('li')[0].get_text().strip().split('\n'))[1],
                            'pdf_link': single_chapter_html.find_all('li')[5].a['href'],
                            'html_link': single_chapter_html.find_all('li')[6].a['href']}
            self.chapters.append(chapter_dict)

    def get_author(self):
        self.author = self.html.find('meta', {'name': 'citation_author'})['content']

    def get_title(self):
        self.title = self.html.find('meta', {'name': 'citation_title'})['content']

    def make_output_dir(self):
        try:
            self.output_dir = self.author + ' - ' + self.title
            Path(self.output_dir).mkdir(exist_ok=False)
        except FileExistsError:
            print(f'The output folder "{self.output_dir}" already exists! Please rename or remove and start again.')

    def download_pdfs(self):
        for chapter in self.chapters:
            chapter['pdf'] = requests.get(self.base_url + chapter['pdf_link']).content


if __name__ == '__main__':
    print('Welcome to Cambridge Core Book Downloader!')
    book = CambridgeCoreBook('10.1017/9781108923859')
    print(book.chapters[0])
