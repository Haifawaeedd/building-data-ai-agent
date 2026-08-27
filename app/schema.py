from app.database import (
    inspect_postgresql_schema,
    schema_to_prompt,
    get_loaded_fiscal_years,
    get_table_row_count
)


ALLOWED_TABLES = {
    "federal_facilities_energy"
}


PRIMARY_TABLE = (
    "federal_facilities_energy"
)


SOURCE_COLUMN_DESCRIPTIONS = {

    "record_id":
        "Internal database record identifier.",

    "federal_organization":
        (
            "Federal organization responsible "
            "for the facility."
        ),

    "fiscal_year":
        (
            "Fiscal year associated with the "
            "facility energy record."
        ),

    "facility":
        "Facility name.",

    "address":
        "Facility address.",

    "city":
        "Facility city or municipality.",

    "province":
        (
            "Province code. Atlantic Canada values "
            "include NS, NB, NL, and PE."
        ),

    "postal_code":
        "Canadian postal code.",

    "building_floor_area_m2":
        (
            "Reported building floor area "
            "in square metres."
        ),

    "electricity_conventional_kwh":
        (
            "Electricity from conventional grid-tied "
            "sources, measured in kWh."
        ),

    "electricity_clean_kwh":
        (
            "Electricity from clean generation sources, "
            "measured in kWh."
        ),

    "electricity_total_kwh":
        (
            "Total reported electricity, "
            "measured in kWh."
        ),

    "natural_gas_m3":
        (
            "Reported natural gas consumption "
            "in cubic metres."
        ),

    "propane_l":
        "Reported propane quantity in litres.",

    "diesel_l":
        (
            "Reported diesel / number 2 oil "
            "quantity in litres."
        ),

    "district_hot_water_gj":
        "District hot-water energy in GJ.",

    "district_steam_gj":
        "District steam energy in GJ.",

    "emissions_electricity_t":
        (
            "Electricity-related emissions "
            "in tonnes."
        ),

    "emissions_stationary_fuels_t":
        (
            "Stationary-fuel emissions "
            "in tonnes."
        ),

    "emissions_district_energy_t":
        (
            "District-energy emissions "
            "in tonnes."
        )
}


def build_semantic_schema_context(
    schema
):

    lines = []


    for (
        table_name,
        columns
    ) in schema.items():

        lines.append(
            f"Table: {table_name}"
        )

        lines.append(
            "Columns:"
        )


        for column in columns:

            name = (
                column["column_name"]
            )


            description = (
                SOURCE_COLUMN_DESCRIPTIONS.get(
                    name,
                    (
                        "No additional semantic "
                        "description."
                    )
                )
            )


            lines.append(
                f"- {name} "
                f"({column['data_type']}): "
                f"{description}"
            )


        lines.append(
            ""
        )


    return "\n".join(
        lines
    ).strip()


dynamic_schema = (
    inspect_postgresql_schema(
        ALLOWED_TABLES
    )
)


if PRIMARY_TABLE not in dynamic_schema:

    raise RuntimeError(
        (
            "Expected PostgreSQL table "
            f"'{PRIMARY_TABLE}' was not found."
        )
    )


DYNAMIC_SCHEMA_CONTEXT = (
    schema_to_prompt(
        dynamic_schema
    )
)


SEMANTIC_LIVE_SCHEMA = (
    build_semantic_schema_context(
        dynamic_schema
    )
)


discovered_columns = {

    column["column_name"]

    for column
    in dynamic_schema[
        PRIMARY_TABLE
    ]
}


LOADED_FISCAL_YEARS = (
    get_loaded_fiscal_years(
        PRIMARY_TABLE
    )
)


DATASET_PROVENANCE = {

    "publisher":
        "Government of Canada",

    "dataset":
        (
            "Greenhouse Gas Emissions Inventory - "
            "Energy Use Related to Individual "
            "Federal Facilities"
        ),

    "fiscal_years":
        LOADED_FISCAL_YEARS,

    "geographic_scope":
        "Atlantic Canada",

    "province_codes":
        [
            "NS",
            "NB",
            "NL",
            "PE"
        ],

    "table":
        PRIMARY_TABLE,

    "loaded_records":
        get_table_row_count(
            PRIMARY_TABLE
        ),

    "source_url":
        (
            "https://open.canada.ca/data/en/dataset/"
            "6bed41cd-9816-4912-a2b8-b0b224909396"
        )
}
