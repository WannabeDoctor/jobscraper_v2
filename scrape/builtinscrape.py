from contextlib import suppress
from json import JSONDecodeError

from requests import HTTPError, RequestException
from tqdm import tqdm

from scrape.company_result import CompanyResult
from scrape.configs import JobScrapeConfig
from scrape.web_scraper import webscrape_results


def parse_results(
    base_url: str, querystring, page: int, config: JobScrapeConfig
) -> list[CompanyResult]:
    """Takes the params provided in main.py and generates dataclasses for
    each job listing in BuiltInNYC, the job name, company info, and so forth.
    """
    company_results = []
    docs = webscrape_results(base_url, querystring=querystring)  # type:ignore
    jobs = [item.get("title") for item in docs["jobs"]]
    job_desc = [item.get("body") for item in docs["jobs"]]
    company_names = [item.get("title") for item in docs["companies"]]
    alii = [item.get("alias") for item in docs["companies"]]
    for idx, company in enumerate(
        tqdm(
            company_names,
            desc=f"Evaluating Companies | Bundle {page} of {config.total_pages}",
            unit="company",
        )
    ):
        alias = alii[idx][9:]
        company_dict = company_lookup(alias)
        results = CompanyResult(
            inner_id=idx,
            alias=alias,
            company_name=company,
            job_name=jobs[idx],
            job_description=job_desc[idx],
            **company_dict,  # type: ignore
        )  # type: ignore
        company_results.append(results)
    return company_results


def company_lookup(company_alias: str):
    """Looks up the company JSON in BuiltInNYC.
    It passes this along to the superceding parse_results method,
    which places it within the CompanyResult dataclass.
    """
    with suppress(
        JSONDecodeError, RequestException, HTTPError, TypeError, AttributeError
    ):
        company_page_url = f"https://api.builtin.com/companies/alias/{company_alias}"
        comp_docs = webscrape_results(company_page_url, querystring={"region_id": "5"})  # type: ignore
        industries = [item.get("name") for item in comp_docs["industries"]]
        data = {
            "street_address": comp_docs.get("street_address_1"),
            "suite": comp_docs.get("street_address_2"),
            "city": comp_docs.get("city"),
            "state": comp_docs.get("state"),
            "zip": comp_docs.get("zip"),
            "mission": comp_docs.get("mission"),
            "url": comp_docs.get("url"),
            "adjectives": comp_docs.get("adjectives"),
            "industries": industries,
            "twitter": comp_docs.get("twitter"),
            "email": comp_docs.get("email"),
        }
        return data
