import re
import string
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path

import PyPDF2
import requests
import roman
from bs4 import BeautifulSoup
from ebooklib import epub
from tqdm import tqdm


class CambridgeCoreBook:
    doi = ''
    title = ''
    author = ''
    chapters = []
    total_directory_pages = 0
    current_directory_page = 0
    html = ''
    base_url = 'https://www.cambridge.org'
    book_url = ''
    output_dir_base = 'output/'
    output_dir = ''
    chapter_dir = ''
    output_filename = ''
    nums_array = PyPDF2.generic.ArrayObject()
    page_index = 0

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
        if self.html.find(attrs={"data-test-id": "paginationSearchResult"}) is None:
            self.total_directory_pages = 1
        else:
            self.total_directory_pages = int(
                self.html.find(attrs={"data-test-id": "paginationSearchResult"}).find('p').get_text().split()[-1])
        self.current_directory_page = 1
        self.book_url = response.url

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
                chapter_dict['first_page'] = chapter_dict['pages'].split('-')[0]
                chapter_dict['last_page'] = chapter_dict['pages'].split('-')[1]
                try:
                    chapter_dict['first_page'] = int(chapter_dict['first_page'])
                    chapter_dict['last_page'] = int(chapter_dict['last_page'])
                    chapter_dict['pagination_type'] = 'arabic'
                except (TypeError, ValueError):
                    chapter_dict['first_page'] = roman.fromRoman(chapter_dict['first_page'].upper())
                    chapter_dict['last_page'] = roman.fromRoman(chapter_dict['last_page'].upper())
                    chapter_dict['pagination_type'] = 'roman'
                chapter_dict['pages_length'] = chapter_dict['last_page'] - chapter_dict['first_page'] + 1
            if single_chapter_html.find(href=re.compile('core-reader')) is not None:
                chapter_dict['html_link'] = single_chapter_html.find(href=re.compile('core-reader'))['href']
            self.chapters.append(chapter_dict)
        if self.current_directory_page < self.total_directory_pages:
            response = ''
            next_page_url = self.book_url + f'?pageNum={self.current_directory_page + 1}'
            try:
                response = requests.get(next_page_url)
            except not response.status_code == 200:
                raise
            self.html = BeautifulSoup(response.text, 'html.parser')
            self.current_directory_page = self.current_directory_page + 1
            self.get_chapters()

    def get_author(self):
        if not self.html.find('meta', {'name': 'citation_author'}):
            self.author = self.html.find('meta', {'name': 'citation_editor'})['content']
        else:
            self.author = self.html.find('meta', {'name': 'citation_author'})['content']

    def get_title(self):
        self.title = self.html.find('meta', {'name': 'citation_title'})['content'].replace(":", "")

    def make_output_dir(self):
        try:
            self.output_dir = self.output_dir_base + f'{self.author.replace(" ", "-")}_{self.title.replace(" ", "-")}/'
            self.chapter_dir = self.output_dir + 'chapters/'
            Path(self.output_dir_base).mkdir(exist_ok=True)
            Path(self.output_dir).mkdir(exist_ok=False)
            Path(self.chapter_dir).mkdir(exist_ok=False)
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
                    # Ensure only valid characters
                    valid_characters = f'-_.() {string.ascii_letters}{string.digits}'
                    chapter_title_for_filename = chapter["title"].replace(" ", "-")
                    valid_chapter_filename = "".join(ch for ch in chapter_title_for_filename if ch in valid_characters)
                    with open(
                            self.chapter_dir +
                            f'{sequence_number:02}_{valid_chapter_filename}_{chapter["pages"]}.{filetype}',
                            'wb') as output_file:
                        output_file.write(chapter[filetype])
                    sequence_number += 1

    def make_page_label_dict_entry_from_chapter(self, chapter):
        # See https://stackoverflow.com/q/61794994 and https://stackoverflow.com/q/61740267
        # PDF 32000-1:2008, page 374--375, 12.4.2 Page Labels
        #
        # Create pagination only where pagination is available, otherwise create none and fall back on the last section
        if 'pagination_type' in chapter.keys():
            # page index of the first page in a labelling range
            self.nums_array.append(PyPDF2.generic.NumberObject(self.page_index))
            # page label dictionary defining the labelling characteristics for the pages in that range
            number_type = PyPDF2.generic.DictionaryObject()
            if chapter['pagination_type'] == 'arabic':
                number_type.update(
                    {PyPDF2.generic.NameObject("/S"): PyPDF2.generic.NameObject(f"/D /St {chapter['first_page']}")})
            elif chapter['pagination_type'] == 'roman':
                number_type.update(
                    {PyPDF2.generic.NameObject("/S"): PyPDF2.generic.NameObject(f"/r /St {chapter['first_page']}")})
            # /Nums Array containing the /PageLabels Number Tree (see 7.9.7)
            self.nums_array.append(number_type)

    def merge_pdfs(self):
        print(f'Merging PDFs.')
        merger = PyPDF2.PdfMerger()
        for chapter in self.chapters:
            pdf = BytesIO(chapter['pdf'])
            bookmark = chapter['title']
            chapter['pdf_length'] = len(PyPDF2.PdfReader(pdf).pages)
            self.make_page_label_dict_entry_from_chapter(chapter)
            # Unfortunately, length in pages is not necessarily the same as length of the PDF file, as Cambridge Core sometimes inserts blank or copyright pages
            self.page_index = self.page_index + chapter['pdf_length']
            merger.append(fileobj=pdf, outline_item=bookmark)
        page_numbers = PyPDF2.generic.DictionaryObject()
        page_numbers.update({PyPDF2.generic.NameObject("/Nums"): self.nums_array})
        page_labels = PyPDF2.generic.DictionaryObject()
        page_labels.update({PyPDF2.generic.NameObject('/PageLabels'): page_numbers})
        merger.output._root_object.update(page_labels)
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
    parser.add_argument('doi', type=str, help='Digital Object Identifier (DOI)', nargs='?')
    args = parser.parse_args()
    print('Welcome to Cambridge Core Book Downloader!')
    if not args.doi:
        args.doi = input('Enter Digital Object Identifier (DOI): ')
    book = CambridgeCoreBook(args.doi)
