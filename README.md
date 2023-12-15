# Cambridge Core Downloader
## Features
- Download book chapter PDFs from Cambridge Core
- Merge chapters into one book PDF
- Bookmark the chapters in the PDF (PDF outline)
- Set the correct pagination: Roman/Arabic ([PDF `/PageLabels`](https://www.w3.org/TR/2014/NOTE-WCAG20-TECHS-20140408/PDF17#PDF17-ex2))
  - NB: Correct pagination is only possible to a certain extent: Sometimes, the Cambridge Core PDFs have pages added or missing, so they do not conform to the theoretical page range they could contain. This cannot be fixed automatically, as it occurs unsystematically and varies from book to book. As this chiefly applies to prefatory materials, most page numbers inside the chapters are correct, however.
- Where available, download book chapter HTMLs and create an EPUB version (experimental)

## How To Use

You will need to have [Git](https://git-scm.com/) and Python 3 with pip/[pipenv](https://pipenv.pypa.io/en/latest/) installed on your computer.
Then [install the dependencies](https://pipenv.pypa.io/en/latest/basics/#example-pipenv-workflow) thusly:

1. Clone this repository  
    ```{shell}
    git clone https://github.com/pcdi/cambridge_core_downloader
    ```
2. Go into the repository
    ```{shell}
    cd cambridge_core_downloader
    ```
3. Install dependencies
    ```{shell}
    pipenv install
    ```
4. Run the app (insert the DOI of the book to download)
    ```{shell}
    pipenv run python ./cambridge_core_downloader.py 10.1017/9781009076012
    ```
5. If you want an EPUB to be generated if HTML files are available, add an `-e` or `--epub` flag:
    ```{shell}
    pipenv run python ./cambridge_core_downloader.py -e 10.1017/9781009076012
    ```
    ```{shell}
    pipenv run python ./cambridge_core_downloader.py --epub 10.1017/9781009076012
    ```