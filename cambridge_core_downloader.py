import re
import string
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path

import pypdf
import requests
import roman
from bs4 import BeautifulSoup
from ebooklib import epub
from tqdm import tqdm


class CambridgeCoreBook:
    doi = ""
    title = ""
    author = ""
    chapters = []
    total_directory_pages = 0
    current_directory_page = 0
    html = ""
    base_url = "https://www.cambridge.org"
    book_url = ""
    output_dir_base = "output/"
    output_dir = ""
    chapter_dir = ""
    output_filename = ""
    nums_array = pypdf.generic.ArrayObject()
    page_index = 0
    valid_characters = f"-_.() {string.ascii_letters}{string.digits}"

    def __init__(self, doi):
        self.doi = doi
        self.get_html()
        self.get_title()
        self.get_author()
        self.make_output_dir()
        self.output_filename = (
            f'{self.author.replace(" ", "-")}_{self.title.replace(" ", "-")}'
        )
        self.get_chapters()
        self.download_files()
        self.merge_pdfs()
        self.make_epub()

    def get_html(self):
        print(f"Getting book information from DOI.")
        doi_url = "https://doi.org/" + self.doi
        response = ""
        try:
            response = requests.get(doi_url)
        except not response.status_code == 200:
            raise
        self.html = BeautifulSoup(response.text, "html.parser")
        if self.html.find(attrs={"data-test-id": "paginationSearchResult"}) is None:
            self.total_directory_pages = 1
        else:
            self.total_directory_pages = int(
                self.html.find(attrs={"data-test-id": "paginationSearchResult"})
                .find("p")
                .get_text()
                .split()[-1]
            )
        self.current_directory_page = 1
        self.book_url = response.url

    def get_chapters(self):
        all_chapters_html = self.html.find_all("ul", class_="details")
        re_pdf = re.compile(r"\.pdf")
        re_core_reader = re.compile("core-reader")
        for single_chapter_html in all_chapters_html:
            if single_chapter_html.find(href=re_pdf) is None:
                continue
            chapter_dict = {
                "title": (
                    single_chapter_html.find("a", class_="part-link")
                    .get_text()
                    .strip()
                    .split("\n")
                )[0],
                "pdf_link": single_chapter_html.find(href=re_pdf)["href"],
                "pages": "",
                "html_link": "",
                "indentation_level": int(
                    [
                        re.split("indent-", classname)
                        for classname in single_chapter_html.parent["class"]
                        if re.match("indent", classname)
                    ][0][-1]
                ),
            }
            if (
                len(
                    single_chapter_html.find("a", class_="part-link")
                    .get_text()
                    .strip()
                    .split("\n")
                )
                == 2
            ):
                chapter_dict["pages"] = (
                    single_chapter_html.find("a", class_="part-link")
                    .get_text()
                    .strip()
                    .split("\n")
                )[1].replace("pp ", "")
                chapter_dict["first_page"] = chapter_dict["pages"].split("-")[0]
                chapter_dict["last_page"] = chapter_dict["pages"].split("-")[1]
                try:
                    chapter_dict["first_page"] = int(chapter_dict["first_page"])
                    chapter_dict["last_page"] = int(chapter_dict["last_page"])
                    chapter_dict["pagination_type"] = "arabic"
                except (TypeError, ValueError):
                    chapter_dict["first_page"] = roman.fromRoman(
                        chapter_dict["first_page"].upper()
                    )
                    chapter_dict["last_page"] = roman.fromRoman(
                        chapter_dict["last_page"].upper()
                    )
                    chapter_dict["pagination_type"] = "roman"
                chapter_dict["pages_length"] = (
                    chapter_dict["last_page"] - chapter_dict["first_page"] + 1
                )
            if single_chapter_html.find(href=re_core_reader) is not None:
                chapter_dict["html_link"] = single_chapter_html.find(
                    href=re_core_reader
                )["href"]
            self.chapters.append(chapter_dict)
        if self.current_directory_page < self.total_directory_pages:
            response = ""
            next_page_url = (
                self.book_url + f"?pageNum={self.current_directory_page + 1}"
            )
            try:
                response = requests.get(next_page_url)
            except not response.status_code == 200:
                raise
            self.html = BeautifulSoup(response.text, "html.parser")
            self.current_directory_page = self.current_directory_page + 1
            self.get_chapters()

    def get_author(self):
        if not self.html.find("meta", {"name": "citation_author"}):
            author_string = self.html.find("meta", {"name": "citation_editor"})[
                "content"
            ]
        else:
            author_string = self.html.find("meta", {"name": "citation_author"})[
                "content"
            ]
        self.author = "".join(
            letter for letter in author_string if letter in self.valid_characters
        )

    def get_title(self):
        title_string = self.html.find("meta", {"name": "citation_title"})["content"]
        self.title = "".join(
            letter for letter in title_string if letter in self.valid_characters
        )

    def make_output_dir(self):
        try:
            self.output_dir = (
                self.output_dir_base
                + f'{self.author.replace(" ", "-")}_{self.title.replace(" ", "-")}/'
            )
            self.chapter_dir = self.output_dir + "chapters/"
            Path(self.output_dir_base).mkdir(exist_ok=True)
            Path(self.output_dir).mkdir(exist_ok=False)
            Path(self.chapter_dir).mkdir(exist_ok=False)
        except FileExistsError:
            print(
                f'The output folder "{self.output_dir}" already exists! Please rename or remove and start again.'
            )
            raise

    def download_files(self):
        for filetype in ["pdf", "html"]:
            if self.chapters[0][f"{filetype}_link"] == "":
                continue
            else:
                print(
                    f'Downloading {filetype.upper()}s for "{self.title}" by {self.author}.'
                )
                sequence_number = 1
                response = ""
                for chapter in tqdm(self.chapters):
                    try:
                        response = requests.get(
                            self.base_url + chapter[f"{filetype}_link"]
                        )
                    except not response.status_code == 200:
                        raise
                    chapter[filetype] = response.content
                    if filetype == "html":
                        self.extract_html(chapter)
                    # Ensure only valid characters
                    chapter_title_for_filename = chapter["title"].replace(" ", "-")
                    valid_chapter_filename = "".join(
                        ch
                        for ch in chapter_title_for_filename
                        if ch in self.valid_characters
                    )
                    with open(
                        self.chapter_dir
                        + f'{sequence_number:02}_{valid_chapter_filename}_{chapter["pages"]}.{filetype}',
                        "wb",
                    ) as output_file:
                        output_file.write(chapter[filetype])
                    sequence_number += 1

    def merge_pdfs(self):
        print(f"Merging PDFs.")
        writer = pypdf.PdfWriter()
        for chapter in self.chapters:
            pdf = pypdf.PdfReader(BytesIO(chapter["pdf"]))
            bookmark = chapter["title"]
            chapter["pdf_length"] = len(pdf.pages)
            # Unfortunately, length in pages is not necessarily the same as length of the PDF file, as Cambridge Core
            # sometimes inserts blank or copyright pages
            writer.append(fileobj=pdf)
            page_index_first = self.page_index
            page_index_last = self.page_index + chapter["pdf_length"] - 1
            if not pdf.outline:
                writer.add_outline_item(
                    title=chapter["title"], page_number=page_index_first
                )
            match chapter["pagination_type"]:
                case "arabic":
                    pagination_style = pypdf.constants.PageLabelStyle.DECIMAL
                case "roman":
                    pagination_style = pypdf.constants.PageLabelStyle.LOWERCASE_ROMAN
                case _:
                    raise KeyError
            writer.set_page_label(
                page_index_from=page_index_first,
                page_index_to=page_index_last,
                style=pagination_style,
                start=chapter["first_page"],
            )
            self.page_index = self.page_index + chapter["pdf_length"]
        writer.write(self.output_dir + "/" + self.output_filename + ".pdf")
        writer.close()
        print("Done.")

    def extract_html(self, chapter):
        chapter_html = BeautifulSoup(chapter["html"], "html.parser")
        chapter["extracted_html"] = chapter_html.find(id="content-container").prettify()

    def make_epub(self):
        if "extracted_html" not in self.chapters[0]:
            print("No HTML available, no EPUB can be made.")
            return
        print("Making EPUB.")
        book = epub.EpubBook()
        book.set_identifier(self.output_filename)
        book.set_title(self.title)
        book.set_language("en")
        book.add_author(self.author)
        book.toc = []
        book.spine = []

        for chapter in self.chapters:
            epub_chapter = epub.EpubHtml(
                title=chapter["title"],
                file_name=chapter["title"].replace(" ", "-") + ".html",
                lang="en",
            )
            epub_chapter.set_content(chapter["extracted_html"])
            book.add_item(epub_chapter)
            book.toc.append(epub_chapter)
            book.spine.append(epub_chapter)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        epub.write_epub(self.output_dir + "/" + self.output_filename + ".epub", book)
        print("Done.")


if __name__ == "__main__":
    parser = ArgumentParser("Download a book from Cambridge Core.")
    parser.add_argument(
        "doi", type=str, help="Digital Object Identifier (DOI)", nargs="?"
    )
    args = parser.parse_args()
    print("Welcome to Cambridge Core Book Downloader!")
    if not args.doi:
        args.doi = input("Enter Digital Object Identifier (DOI): ")
    book = CambridgeCoreBook(args.doi)
