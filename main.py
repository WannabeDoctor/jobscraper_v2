from time import perf_counter

from tqdm import tqdm

from scrape.builtinscrape import parse_results
from scrape.configs import read_config
from scrape.coverletterwriter import CoverLetterWriter
from scrape.log import logger
from scrape.namefetcher import NameFetcher

config, persona = read_config("./config.json")
querystring = config.querystring
builtinnyc = config.url_builtin


def main() -> None:
    """jobscraper takes the provided querystring, searches for job results,
    and for each of those job results generates a cover letter.
    """
    start = perf_counter()
    for page in range(0, config.total_pages):
        page_dict = {"page": page}
        querystring.update(page_dict)
        company_collection = parse_results(builtinnyc, querystring, page, config)

        for idx, company in enumerate(
            tqdm(company_collection, desc="Writing Letter", unit="contact")
        ):
            business_card = NameFetcher(
                company=company, config=config
            ).parse_provided_search_queries()

            logger.info(
                "Writing cover letter to %s at %s for the role of %s",
                business_card.fullname,
                business_card.workplace,
                company_collection[idx].job_name,
            )  # type: ignore
            CoverLetterWriter(
                company, contact=business_card, persona=persona, config=config
            ).write()

    elapsed = perf_counter() - start
    logger.info("Job search finished in %s seconds.", elapsed)  # type: ignore


if __name__ == "__main__":
    main()
