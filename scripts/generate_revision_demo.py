"""Build-only synthetic Rev3 PDF; never edits canonical evidence JSON or Rev2."""

from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import generate_document_corpus as corpus


def main():
    document = corpus.DOCUMENTS[0]
    def changed(text):
        return (text.replace("A25-6205", "A30-6206")
                .replace("Nominal bore class: 25 mm", "Nominal bore class: 30 mm")
                .replace("Bore diameter | 25 mm", "Bore diameter | 30 mm")
                .replace("-R2", "-R3"))
    pages = tuple(replace(page, subtitle=changed(page.subtitle), sections=tuple(
        (heading, tuple(changed(line) for line in lines)) for heading, lines in page.sections
    )) for page in document.pages)
    revision = replace(document, filename="Candidate_A_Datasheet_Rev3.pdf", revision="3", effective_date="2026-10-22", pages=pages)
    corpus.OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "demo"
    corpus.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(corpus.build_document(revision))


if __name__ == "__main__":
    main()
