import pycountry
from pydantic import BaseModel, Field, field_validator


class CreateCampaign(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    geo_codes: list[str] = Field(min_length=1)
    keitaro_offer_id: int = Field(gt=0)
    domain_keitaro_id: int = Field(gt=0)
    group_keitaro_id: int = Field(gt=0)
    source_keitaro_id: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, name: str) -> str:
        if not name.strip():
            raise ValueError("Укажите название кампании")
        return name.strip()

    @field_validator("geo_codes")
    @classmethod
    def countries(cls, values: list[str]) -> list[str]:
        result = list(dict.fromkeys(value.strip().upper() for value in values))
        if any(pycountry.countries.get(alpha_2=code) is None for code in result):
            raise ValueError("Неизвестный код страны")
        return result


class OfferID(BaseModel):
    keitaro_offer_id: int = Field(gt=0)


class Pin(BaseModel):
    pinned: bool
