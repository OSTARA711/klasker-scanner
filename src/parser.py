"""HTML and JSON-LD parsing for Klasker Scanner."""

import json
from html.parser import HTMLParser


class HTMLMetadataParser(HTMLParser):
    """Extract basic HTML metadata and JSON-LD."""

    def __init__(self):
        super().__init__()

        self.title = ""
        self.description = ""
        self.canonical = ""
        self.og = {}

        self.json_ld = []
        self._json_ld_active = False
        self._json_ld_parts = []

        self._inside_title = False
        self._title_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "title":
            self._inside_title = True
            self._title_parts = []

        elif tag == "meta":
            name = attrs.get("name", "").lower()
            property_name = attrs.get("property", "").lower()
            content = attrs.get("content", "")

            if name == "description":
                self.description = content

            if property_name.startswith("og:"):
                self.og[property_name] = content

        elif tag == "link":
            rel = attrs.get("rel", "").lower()

            if "canonical" in rel:
                self.canonical = attrs.get("href", "")

        elif tag == "script":
            script_type = attrs.get("type", "").lower()

            if script_type == "application/ld+json":
                self._json_ld_active = True
                self._json_ld_parts = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._inside_title = False
            self.title = "".join(self._title_parts).strip()

        elif tag == "script" and self._json_ld_active:
            raw_json = "".join(self._json_ld_parts).strip()

            if raw_json:
                try:
                    parsed = json.loads(raw_json)

                    if isinstance(parsed, list):
                        self.json_ld.extend(parsed)
                    else:
                        self.json_ld.append(parsed)

                except json.JSONDecodeError:
                    # Invalid JSON-LD must not prevent the rest
                    # of the website from being scanned.
                    pass

            self._json_ld_active = False
            self._json_ld_parts = []

    def handle_data(self, data):
        if self._inside_title:
            self._title_parts.append(data)

        if self._json_ld_active:
            self._json_ld_parts.append(data)


def json_ld_types(data):
    """Return @type values from one JSON-LD object."""

    types = []

    if not isinstance(data, dict):
        return types

    value = data.get("@type")

    if isinstance(value, str):
        types.append(value)

    elif isinstance(value, list):
        types.extend(
            item for item in value
            if isinstance(item, str)
        )

    return types


def extract_json_ld(json_ld):
    """Extract recognised structured-data types from JSON-LD."""

    products = []
    offers = []
    organisations = []
    brands = []
    ratings = []
    types = []

    def inspect(item):
        if not isinstance(item, dict):
            return

        item_types = json_ld_types(item)

        for item_type in item_types:
            if item_type not in types:
                types.append(item_type)

        normalised_types = {
            item_type.lower()
            for item_type in item_types
        }

        if "product" in normalised_types:
            products.append(item)

        if (
            "offer" in normalised_types
            or "aggregateoffer" in normalised_types
        ):
            offers.append(item)

        if (
            "organization" in normalised_types
            or "organisation" in normalised_types
            or "localbusiness" in normalised_types
        ):
            organisations.append(item)

        if "brand" in normalised_types:
            brands.append(item)

        if (
            "aggregaterating" in normalised_types
            or "rating" in normalised_types
        ):
            ratings.append(item)

        # JSON-LD can contain nested structured objects.
        for value in item.values():

            if isinstance(value, dict):
                inspect(value)

            elif isinstance(value, list):
                for nested in value:
                    if isinstance(nested, dict):
                        inspect(nested)

    for item in json_ld:
        inspect(item)

    return {
        "detected": bool(json_ld),
        "types": types,
        "products": products,
        "offers": offers,
        "organisations": organisations,
        "brands": brands,
        "ratings": ratings,
    }
