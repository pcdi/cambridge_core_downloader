# Cambridge Core Downloader
## Features
- Download book chapter PDFs from Cambridge Core
- Merge chapters into one book PDF
- Bookmark the chapters in the PDF (PDF outline)
- Set the correct pagination: Roman/Arabic ([PDF `/PageLabels`](https://www.w3.org/TR/2014/NOTE-WCAG20-TECHS-20140408/PDF17#PDF17-ex2))
- Where available, download book chapter HTMLs and create an EPUB version (experimental)

## How To Use

You will need to have [Git](https://git-scm.com/) and Python 3 with pip/[pipenv](https://pipenv.pypa.io/en/latest/) installed on your computer.
Then [install the dependencies](https://pipenv.pypa.io/en/latest/basics/#example-pipenv-workflow) thusly:

```{shell}
# Clone this repository
$ git clone https://github.com/pcdi/cambridge_core_downloader

# Go into the repository
$ cd cambridge_core_downloader

# Install dependencies
$ pipenv install

# Run the app (insert the DOI of the book to download)
$ pipenv run python ./cambridge_core_downloader.py 10.1017/9781009076012
```