from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
import re
from typing import Any

from pydantic import BaseModel, Field, model_validator


class EventType(StrEnum):
    impression = "impression"
    view = "view"
    click = "click"
    add_to_cart = "add_to_cart"
    purchase = "purchase"
    return_item = "return" 


class Article(BaseModel):
    article_id: str
    name: str = "Fashion item"
    description: str = ""
    product_type: str
    department: str
    colour_group: str
    price: float = Field(ge=0)
    available: bool = True
    index_group: str = "unknown"
    section: str = "unknown"


def article_audience(article: Article) -> str:
    """Return the catalog-backed audience, leaving ambiguous items unclassified."""
    group = article.index_group.casefold()
    section = article.section.casefold()

    if group in {"baby/children"} or re.search(r"\b(baby|kids?|children|young boy|young girl)\b", section):
        return "KIDS"
    if group == "menswear":
        return "MEN"
    if group in {"ladieswear", "divided"}:
        return "WOMEN"
    if re.search(r"\b(menswear|men)\b", section) and not re.search(r"\bwomen\b", section):
        return "MEN"
    if re.search(r"\b(ladies|women|mama|divided)\b", section):
        return "WOMEN"
    return ""


def article_category(article: Article) -> str:
    """Map catalog product types to the storefront's fixed category taxonomy."""
    value = article.product_type.casefold()
    if re.search(r"trouser|pants|jeans|shorts|skirt|legging|tights|jogger|dungaree|sarong|overall|underwear bottom|underwear tights|swimwear bottom|pyjama bottom|long john", value):
        return "Trousers & bottoms"
    if re.search(r"dress|jumpsuit|playsuit|gown|frock|underdress", value):
        return "Dresses"
    if re.search(r"t-shirt|tee|blouse|polo|shirt|top|vest|sweater|knit|sweatshirt|bodysuit|bra|lingerie|pyjama|nightwear|bikini|camisole|swimwear|swimsuit|underwear|corset|garment set", value):
        return "T-shirts & tops"
    if re.search(r"jacket|coat|blazer|cardigan|hoodie|parka|waistcoat|robe|outerwear", value):
        return "Jackets & layers"
    if re.search(r"shoe|boot|sandal|sneaker|loafer|heel|slipper|ballerina|pump|wedge|moccasin|flip flop|pre-walk|bootie", value):
        return "Shoes"
    if re.search(r"bag|backpack|bumbag|tote|wallet|belt|scarf|hat|beanie|cap|accessor|sock|leg warmer|earring|necklace|bracelet|jewel|ring|sunglass|watch|glove|suspender|brace|tie|hair|headband|alice|clip|keychain|umbrella|eyeglass", value):
        return "Accessories"
    return "All"


def article_matches_collection(article: Article, collection: str) -> bool:
    """Match special storefront edits only when catalog metadata supports them."""
    department = article.department.casefold().strip()
    section = article.section.casefold().strip()
    product_type = article.product_type.casefold().strip()

    if collection == "BEAUTY":
        if article_audience(article) == "KIDS":
            return False
        name_and_description = f"{article.name} {article.description}".casefold()
        if re.search(r"\bbags?\b|(?:cosmetic|make[- ]?up|lipstick)\s*bags?\b", name_and_description):
            return False
        if re.search(
            r"cosmetic|fragrance|perfume|make.?up|skin.?care|hair.?care|nail.?care|shampoo|conditioner|lip.?balm|lipstick|deodorant|bath.?bomb",
            product_type,
        ):
            return True
        if article_category(article) not in {"Accessories", "All"}:
            return False
        return bool(re.search(
            r"perfume|fragrance|eau de parfum|eau de toilette|shampoo|conditioner|skin.?care|hair.?care|nail polish|lip.?balm|lipstick|foundation|mascara|eyeliner|deodorant|lotion|bath.?bomb",
            name_and_description,
        ))
    if collection == "STUDIO":
        markers = {"studio collection", "limited edition", "special collection", "special collections", "conscious exclusive", "collaborations"}
        return department in markers or section in markers
    if collection == "SALE":
        return bool(re.search(r"promotion\s*/?\s*other\s*/?\s*offer|price items", department))
    return False


class Interaction(BaseModel):
    customer_id: str
    article_id: str
    event_type: EventType
    event_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExperimentVariant(BaseModel):
    name: str
    allocation: int = Field(ge=0, le=10_000)


class Experiment(BaseModel):
    experiment_id: str
    variants: list[ExperimentVariant]
    status: str = "running"

    @model_validator(mode="after")
    def validate_variants(self) -> Experiment:
        if not self.variants:
            raise ValueError("an experiment must define at least one variant")
        names = [variant.name for variant in self.variants]
        if any(not name.strip() for name in names) or len(names) != len(set(names)):
            raise ValueError("experiment variant names must be non-empty and unique")
        if sum(variant.allocation for variant in self.variants) != 10_000:
            raise ValueError("experiment variant allocations must sum to 10000 basis points")
        return self


class Recommendation(BaseModel):
    article_id: str
    position: int
    score: float
    source: str


class RecommendationResponse(BaseModel):
    request_id: str
    customer_id: str
    surface: str
    experiment_id: str
    variant: str
    model_version: str
    recommendations: list[Recommendation]


class EventRequest(BaseModel):
    event_type: EventType
    customer_id: str
    article_id: str | None = None
    surface: str = "unknown"
    request_id: str | None = None
    experiment_id: str | None = None
    variant: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoredEvent(EventRequest):
    event_id: str
    event_time: datetime


class AuthRequest(BaseModel):
    login_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=4, max_length=128)


class AuthResponse(BaseModel):
    login_id: str
    customer_id: str
    created: bool = False
