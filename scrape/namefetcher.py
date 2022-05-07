import re
from contextlib import suppress
from dataclasses import dataclass

from bs4 import BeautifulSoup
from googlesearch import search
from nltk.corpus import names, webtext
from requests.exceptions import (HTTPError, ProxyError, RequestException,
                                 Timeout)
from tld import get_tld

from scrape.company_result import CompanyResult
from scrape.configs import JobScrapeConfig
from scrape.log import logger
from scrape.web_scraper import webscrape_results


@dataclass(order=True)
class BusinessCard:
    """_summary_"""

    greeting: str
    fname: str
    surname: str
    fullname: str
    workplace: str


class NameFetcher:
    """_summary_"""

    def __init__(
        self,
        company: CompanyResult,
        config: JobScrapeConfig,
    ):
        self.company = company
        self.config = config

        with open(config.brand_names, "r", encoding="utf8") as f:
            brand_names = set(f.readlines())
            self.set_of_brandnames: set[str] = {
                brand.strip("\n") for brand in brand_names
            }

        self.set_of_firstnames: set[str] = set(names.words())
        self.set_webtext: set[str] = set(webtext.words())
        self.greeting: str = "To"
        self.first: str = "Whom It"
        self.last: str = "May Concern"

    def generate_urls_from_search_query(self):
        """generate_urls_from_search_query searches google for urls matching its provided search query.

        Returns:
            A Generator that yields URL paths to be assessed or requested.
        """
        return search(
            query=f'"{self.company.company_name}" \
                            {self.config.search_query}',
            start=0,
            stop=3,
            pause=4,
            country="US",
            verify_ssl=False,
        )

    def parse_provided_search_queries(self) -> BusinessCard:
        """parse_provided_search_queries searches for contact information based on urls and source page data.

        Returns:
            BusinessCard: A dataclass containing the contact's contact information and company.
        """

        linkedin = self.config.site_queries[0]
        search_results: list[str] = self.generate_urls_from_search_query()
        for link in search_results:
            logger.info("Getting: %s | %s", link, self.company.company_name)

            if linkedin in link:
                (
                    self.greeting,
                    self.first,
                    self.last,
                ) = self.fetch_names_from_linkedin_urls(link)

            elif link.startswith(
                self.config.site_queries[1]
                or self.config.site_queries[2]
                or self.config.site_queries[3],
            ):
                logger.error("Skipping: %s, as it is a reserved url.", link)

            elif [brand for brand in self.set_of_brandnames if brand in link] != 0:
                logger.debug("Brand matches found...")
                try:
                    response = webscrape_results(link, run_beautiful_soup=True)
                    (
                        self.greeting,
                        self.first,
                        self.last,
                    ) = self.fetch_names_from_page_sources(response)
                except (
                    TypeError,
                    HTTPError,
                    AttributeError,
                    ConnectionError,
                    ProxyError,
                    Timeout,
                    IndexError,
                    ValueError,
                    RequestException,
                ) as error_found:
                    logger.error(error_found)

            elif len([brand for brand in self.set_of_brandnames if brand in link]) == 0:
                logger.debug("no brand matches found")
                username = get_tld(link, fail_silently=True, as_object=True).domain  # type: ignore
                (
                    self.greeting,
                    self.first,
                    self.last,
                ) = self.compare_username_against_firstnames_set(username)

            else:
                try:
                    response = webscrape_results(link, run_beautiful_soup=True)
                    (
                        self.greeting,
                        self.first,
                        self.last,
                    ) = self.fetch_names_from_page_sources(response)
                except (
                    TypeError,
                    AttributeError,
                    HTTPError,
                    ConnectionError,
                    ProxyError,
                    Timeout,
                    IndexError,
                    ValueError,
                    RequestException,
                ) as error_found:
                    logger.error(error_found)

        return BusinessCard(
            greeting=self.greeting,
            fname=self.first,
            surname=self.last,
            fullname=f"{self.first} {self.last}",
            workplace=self.company.company_name,
        )

    def fetch_names_from_page_sources(
        self, soup: BeautifulSoup
    ) -> tuple[str, str, str]:
        """fetch_names_from_page_sources takes a page source object from BeautifulSoup
            and from it extracts a self.first and self.last name.

        Args:
            soup (BeautifulSoup): a BeautifulSoup object that contains the page source info to be assessed.

        Returns:
            tuple[str,str]: A tuple containing a self.first and self.last name.
        """
        soup_text = soup.text.split(" ")
        all_text: list[str] = [word for word in soup_text]
        entire_body: list[str] = [
            word for word in all_text if word.lower() not in self.set_webtext
        ]
        first_names = [
            word
            for word in entire_body
            if word.title() in self.set_of_firstnames and len(word)
        ]

        try:
            self.first = max(first_names, key=len)
        except ValueError as error_found:
            logger.error(error_found)

        with suppress(TypeError, IndexError):
            full_names = next_grams(entire_body, self.first)
            logger.info(full_names)
            for name in full_names:
                logger.info(name)
                if name[1] in self.set_of_brandnames:
                    logger.info(
                        "%s is for a brand, or is otherwise invalid. We encourage further review. Proceeding to next name.",
                        name,
                    )
                elif name[1] is None:
                    logger.info(f"{name} is not a name.")
                self.greeting, self.first, self.last = "Dear", name[0], name[1]
        return self.greeting, self.first, self.last

    def fetch_names_from_linkedin_urls(self, link: str) -> tuple[str, str, str]:
        """fetch_names_from_linkedin_urls takes a URL from LinkedIn and,
        assuming it is a vanity sting, extracts the name accordingly.

        Args:
            link (str): A LinkedIn URL

        Returns:
            tuple[str,str,str]: A tuple containing a self.greeting, self.first, and self.last name.
        """
        username = fetch_username_str_from_link(link)

        # split out the vanity url into a list.
        # the self.first part of the url will almost definitely have it.
        counter = username.count("-")
        logger.info(f"{counter}-dashes found in username: \n {username}")

        if counter == 0:
            (
                self.greeting,
                self.first,
                self.last,
            ) = self.compare_username_against_firstnames_set(username)

        elif counter == 1:
            self.first, self.last = username.split("-", maxsplit=1)
            self.greeting, self.first, self.last = (
                "Dear",
                self.first.title(),
                self.last.title(),
            )

        elif counter >= 2:
            self.first, middle, self.last, *_ = username.split("-", maxsplit=counter)
            if re.findall(r"\d+", self.last):
                self.last = middle
            else:
                self.first.join(f" {middle}")
                # if the titlecase matches, then it's a match and we can return the result
            self.greeting, self.first, self.last = (
                "Dear",
                self.first.title(),
                self.last.title(),
            )

        return self.greeting, self.first, self.last

    def compare_username_against_firstnames_set(self, username: str):
        """compare_username_against_firstnames_set _summary_

        Args:
            username (str): _description_

        Returns:
            _type_: _description_
        """
        self.greeting = "Dear"
        first_candidates = [
            first_name.strip()
            for first_name in self.set_of_firstnames
            if first_name.lower() in username and username.find(first_name.lower()) == 0
        ]
        len_first_candidates = len(first_candidates)

        if (
            len_first_candidates == 1
        ):  # if only one candidate match found, that's the only match so it gets returned
            self.first = first_candidates[0].title()
            self.last = username[len(self.first) + 1 :].title()

        elif len_first_candidates >= 2:
            # if multiple matches found, then go for the
            # longest one as that's likely to be the whole name
            logger.info(first_candidates)
            self.first = max(first_candidates, key=len).title()
            logger.info(self.first)
            self.last = username[len(self.first) :].title()
            logger.info(self.last)

        else:  # if no other matches, but a username is present,
            # split that username down the middle as close as
            # possible and edit it later.
            fname_len = len(username) // 2
            self.first, self.last = (
                username[:fname_len].title(),
                username[fname_len - 1 :].title(),
            )
        return self.greeting, self.first, self.last


def next_grams(
    target_list: list, target_name: str, num_grams: int = 1
) -> list[tuple[str, str]]:
    """next_grams [summary]

    Args:
        target_list (list): [description]
        target_name (str): [description]
        n (int, optional): [description]. Defaults to 1.

    Returns:
        list[tuple[str,str]]: Return a list of n-grams (tuples of n successive words) for this
    blob, which in this case is the self.first and self.last name.
    """
    return [
        (target_list[i], (upper_camel_case_split(str(target_list[i + num_grams])))[0])
        for i, word in enumerate(target_list)
        if word is target_name
    ]


def upper_camel_case_split(text: str) -> list:
    """camel_case_split splits strings if they're in CamelCase and need to be not Camel Case.

    Args:
        str (str): The target string to be split.

    Returns:
        list: A list of the words split up on account of being Camel Cased.
    """
    return re.findall(r"[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))", text)


def fetch_username_str_from_link(link: str) -> str:
    """fetch_username_str_from_link _summary_

    Args:
        link (str): _description_

    Returns:
        str: _description_
    """
    logger.info(link)

    # split up linkedin url so that the vanity content is on the right
    if "/in/" in link:
        __prefix, __sep, username = link.partition("/in/")
        i = min(username.find("?"), username.find("/"))
        username = username[:i].strip()
    else:
        username = get_tld(link, fail_silently=True, as_object=True).domain  # type: ignore
    logger.info(username)
    return username
