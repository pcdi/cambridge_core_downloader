import re
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path

import PyPDF2
import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from tqdm import tqdm


class CambridgeCoreBook:
    doi = ''
    title = ''
    author = ''
    chapters = []
    html = ''
    base_url = 'https://www.cambridge.org'
    output_dir = ''
    chapter_dir = ''
    output_filename = ''

    def __init__(self, doi):
        self.doi = doi
        self.get_html()
        self.get_title()
        self.get_author()
        self.make_output_dir()
        self.output_filename = f'{self.author.replace(" ", "-")}_{self.title.replace(" ", "-")}'
        self.get_chapters()
        self.download_files()
        self.merge_pdfs()
        self.make_epub()

    def get_html(self):
        print(f'Getting book information from DOI.')
        doi_url = 'https://doi.org/' + self.doi
        response = ''
        try:
            response = requests.get(doi_url)
        except not response.status_code == 200:
            raise
        self.html = BeautifulSoup(response.text, 'html.parser')

    def get_chapters(self):
        all_chapters_html = self.html.find_all('ul', class_='details')
        for single_chapter_html in all_chapters_html:
            if single_chapter_html.find(href=re.compile('\.pdf')) is None:
                continue
            chapter_dict = {
                'title': (single_chapter_html.find('a', class_='part-link').get_text().strip().split('\n'))[0],
                'pdf_link': single_chapter_html.find(href=re.compile('\.pdf'))['href'],
                'pages': '',
                'html_link': '',
                'indentation_level': int(
                    [re.split('indent-', classname) for classname in single_chapter_html.parent['class'] if
                     re.match('indent', classname)][0][-1])}
            if len(single_chapter_html.find('a', class_='part-link').get_text().strip().split('\n')) == 2:
                chapter_dict['pages'] = \
                    (single_chapter_html.find('a', class_='part-link').get_text().strip().split('\n'))[1].replace(
                        'pp ', '')
            if single_chapter_html.find(href=re.compile('core-reader')) is not None:
                chapter_dict['html_link'] = single_chapter_html.find(href=re.compile('core-reader'))['href']
            self.chapters.append(chapter_dict)

    def get_author(self):
        if not self.html.find('meta', {'name': 'citation_author'}):
            self.author = self.html.find('meta', {'name': 'citation_editor'})['content']
        else:
            self.author = self.html.find('meta', {'name': 'citation_author'})['content']

    def get_title(self):
        self.title = self.html.find('meta', {'name': 'citation_title'})['content'].replace(":", "")

    def make_output_dir(self):
        try:
            self.output_dir = f'{self.author.replace(" ", "-")}_{self.title.replace(" ", "-")}/'
            self.chapter_dir = self.output_dir + 'chapters/'
            Path(self.output_dir).mkdir(exist_ok=True)
            Path(self.chapter_dir).mkdir(exist_ok=True)
        except FileExistsError:
            print(f'The output folder "{self.output_dir}" already exists! Please rename or remove and start again.')
            raise

    def download_files(self):
        for filetype in ['pdf', 'html']:
            if self.chapters[0][f'{filetype}_link'] == '':
                continue
            else:
                print(f'Downloading {filetype.upper()}s for "{self.title}" by {self.author}.')
                sequence_number = 1
                response = ''
                for chapter in tqdm(self.chapters):
                    try:
                        response = requests.get(self.base_url + chapter[f'{filetype}_link'])
                    except not response.status_code == 200:
                        raise
                    chapter[filetype] = response.content
                    if filetype == 'html':
                        self.extract_html(chapter)
                    with open(
                            self.chapter_dir +
                            f'{sequence_number:02}_{chapter["title"].replace(" ", "-")}_{chapter["pages"]}.{filetype}',
                            'wb') as output_file:
                        output_file.write(chapter[filetype])
                    sequence_number += 1

    def merge_pdfs(self):
        print(f'Merging PDFs.')
        merger = PyPDF2.PdfMerger()
        for chapter in self.chapters:
            pdf = BytesIO(chapter['pdf'])
            bookmark = chapter['title']
            merger.append(fileobj=pdf, outline_item=bookmark)
        merger.write(self.output_dir + '/' + self.output_filename + '.pdf')
        merger.close()
        print('Done.')

    def extract_html(self, chapter):
        chapter_html = BeautifulSoup(chapter['html'], 'html.parser')
        chapter['extracted_html'] = chapter_html.find(id='content-container').prettify()

    def make_epub(self):
        if 'extracted_html' not in self.chapters[0]:
            print('No HTML available, no EPUB can be made.')
            return
        print('Making EPUB.')
        book = epub.EpubBook()
        book.set_identifier(self.output_filename)
        book.set_title(self.title)
        book.set_language('en')
        book.add_author(self.author)
        book.toc = []
        book.spine = []

        for chapter in self.chapters:
            epub_chapter = epub.EpubHtml(title=chapter['title'],
                                         file_name=chapter['title'].replace(" ", "-") + '.html',
                                         lang='en')
            epub_chapter.set_content(chapter['extracted_html'])
            book.add_item(epub_chapter)
            book.toc.append(epub_chapter)
            book.spine.append(epub_chapter)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        epub.write_epub(self.output_dir + '/' + self.output_filename + '.epub', book)
        print('Done.')


if __name__ == '__main__':
    parser = ArgumentParser('Download a book from Cambridge Core.')
    parser.add_argument('doi', type=str, help='Digital Object Identifier (DOI)')
    args = parser.parse_args()
    print('Welcome to Cambridge Core Book Downloader!')
    book = CambridgeCoreBook(args.doi)
