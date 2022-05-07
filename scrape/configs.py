import json
from dataclasses import dataclass, field


@dataclass
class PersonaConfig:
    """A dataclass containing information on you, the applicant."""

    name: str
    role: str
    values: str
    my_background: str
    years: str
    services: str
    email: str
    portfolio: str
    phone_number: str
    signature: str
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)


@dataclass
class JobScrapeConfig:
    """A dataclass containing information on both the job query and cover letter settings."""

    export_dir: str
    url_builtin: str
    brand_names: str
    surnames: str
    total_pages: int
    per_page: int
    search_query: str
    font_regular: str
    font_bold: str
    font_italic: str
    font_bolditalic: str
    header: dict = field(default_factory=dict)
    excitement_words: list[str] = field(default_factory=list)
    site_queries: list[str] = field(default_factory=list)
    querystring: dict = field(default_factory=dict)
    persona: dict = field(default_factory=dict)


def read_config(config_file: str):
    """read_config takes the json configuration file and returns the
    configuration and information about you, the applicant.

    Args:
        config_file (str): a .json file containing the configuration information.

    Returns:
        Both the JobScrapeConfig and the PersonaConfig
    """
    with open(config_file, encoding="utf-8") as file:
        data = json.load(file)
        persona = data["persona"]
        return JobScrapeConfig(**data), PersonaConfig(**persona)
