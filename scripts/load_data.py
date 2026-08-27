import os

import pandas as pd
import psycopg
from psycopg import sql


SOURCE_CSV_PATH = os.getenv(
    "SOURCE_CSV_PATH",
    "/data/source.csv"
)


ADMIN_DATABASE_URL = os.environ[
    "ADMIN_DATABASE_URL"
]


READONLY_DB_PASSWORD = os.environ[
    "READONLY_DB_PASSWORD"
]


READONLY_ROLE = (
    "readonly_agent"
)


TARGET_TABLE = (
    "federal_facilities_energy"
)


ATLANTIC_PROVINCES = [
    "NS",
    "NB",
    "NL",
    "PE"
]


PROVINCE_MAP = {

    # Full English names
    "Nova Scotia":
        "NS",

    "New Brunswick":
        "NB",

    "Newfoundland and Labrador":
        "NL",

    "Newfoundland & Labrador":
        "NL",

    "Prince Edward Island":
        "PE",

    # Already-normalized codes
    "NS":
        "NS",

    "NB":
        "NB",

    "NL":
        "NL",

    "PE":
        "PE"
}


NUMERIC_COLUMNS = [

    "Building floor area (m2)",

    (
        "Electricity from Conventional "
        "Grid-Tied Sources (kWh)"
    ),

    (
        "Electricity from Clean Generation "
        "Sources (kWh)"
    ),

    "Electricity total (kWh)",

    "Natural gas (m³)",

    "Propane (L)",

    "Diesel (#2 oil) (L)",

    "District energy - Hot water (GJ)",

    "District energy - Steam (GJ)",

    "Emissions - Electricity (t)",

    "Emissions - Stationary fuels (t)",

    "Emissions - District energy (t)"
]


SOURCE_COLUMNS = [

    "Federal organization",
    "Fiscal year",
    "Facility",
    "Address",
    "City",
    "Province",
    "Postal code",

    "Building floor area (m2)",

    (
        "Electricity from Conventional "
        "Grid-Tied Sources (kWh)"
    ),

    (
        "Electricity from Clean Generation "
        "Sources (kWh)"
    ),

    "Electricity total (kWh)",

    "Natural gas (m³)",

    "Propane (L)",

    "Diesel (#2 oil) (L)",

    "District energy - Hot water (GJ)",

    "District energy - Steam (GJ)",

    "Emissions - Electricity (t)",

    "Emissions - Stationary fuels (t)",

    "Emissions - District energy (t)"
]


SQL_COLUMNS = [

    "federal_organization",
    "fiscal_year",
    "facility",
    "address",
    "city",
    "province",
    "postal_code",

    "building_floor_area_m2",

    "electricity_conventional_kwh",

    "electricity_clean_kwh",

    "electricity_total_kwh",

    "natural_gas_m3",

    "propane_l",

    "diesel_l",

    "district_hot_water_gj",

    "district_steam_gj",

    "emissions_electricity_t",

    "emissions_stationary_fuels_t",

    "emissions_district_energy_t"
]


def prepare_dataframe():

    print(
        "Loading source CSV:",
        SOURCE_CSV_PATH
    )


    df = pd.read_csv(
        SOURCE_CSV_PATH
    )


    print(
        "Raw rows:",
        len(df)
    )


    df.columns = [

        column.strip()

        for column
        in df.columns
    ]


    for column in df.columns:

        if df[column].dtype == "object":

            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )


    # Remove non-record footer rows

    df = df[
        df["Fiscal year"].notna()
    ].copy()


    for column in NUMERIC_COLUMNS:

        cleaned = (

            df[column]
            .astype("string")
            .str.strip()
            .replace(
                r"^\s*-\s*$",
                pd.NA,
                regex=True
            )
            .str.replace(
                ",",
                "",
                regex=False
            )
        )


        df[column] = pd.to_numeric(

            cleaned,

            errors="coerce"
        )


    # Normalize full province names to the compact
    # codes used by the application.

    # Government CSV province codes contain
    # surrounding whitespace, e.g. " NB ", " NS ".
    # Normalize whitespace before filtering.

    df["Province"] = (
        df["Province"]
        .astype("string")
        .str.strip()
    )


    df["Province"] = (
        df["Province"]
        .replace(
            PROVINCE_MAP
        )
    )


    print(
        "Normalized Atlantic province counts:"
    )


    print(
        df[
            df["Province"].isin(
                ATLANTIC_PROVINCES
            )
        ][
            "Province"
        ].value_counts()
    )


    df = df[
        df["Province"].isin(
            ATLANTIC_PROVINCES
        )
    ].copy()


    df = df[
        SOURCE_COLUMNS
    ].copy()


    df.columns = (
        SQL_COLUMNS
    )


    print(
        "Atlantic records:",
        len(df)
    )


    print(
        "Province distribution:"
    )


    print(
        df[
            "province"
        ].value_counts()
    )


    return df


def configure_database(
    dataframe
):

    with psycopg.connect(
        ADMIN_DATABASE_URL
    ) as connection:

        with connection.cursor() as cursor:

            # ------------------------------------------------
            # Create or refresh dedicated runtime role
            # ------------------------------------------------

            cursor.execute(

                """
                SELECT 1
                FROM pg_roles
                WHERE rolname = %s;
                """,

                (
                    READONLY_ROLE,
                )
            )


            role_exists = (
                cursor.fetchone()
                is not None
            )


            if not role_exists:

                cursor.execute(

                    sql.SQL(
                        """
                        CREATE ROLE {}
                        LOGIN
                        PASSWORD {};
                        """
                    ).format(

                        sql.Identifier(
                            READONLY_ROLE
                        ),

                        sql.Literal(
                            READONLY_DB_PASSWORD
                        )
                    )
                )


            else:

                cursor.execute(

                    sql.SQL(
                        """
                        ALTER ROLE {}
                        PASSWORD {};
                        """
                    ).format(

                        sql.Identifier(
                            READONLY_ROLE
                        ),

                        sql.Literal(
                            READONLY_DB_PASSWORD
                        )
                    )
                )


            # ------------------------------------------------
            # Explicitly restrict runtime role
            # ------------------------------------------------

            cursor.execute(

                sql.SQL(
                    """
                    ALTER ROLE {}
                    NOSUPERUSER
                    NOCREATEDB
                    NOCREATEROLE
                    NOREPLICATION;
                    """
                ).format(

                    sql.Identifier(
                        READONLY_ROLE
                    )
                )
            )


            # Default every runtime transaction to READ ONLY.

            cursor.execute(

                sql.SQL(
                    """
                    ALTER ROLE {}
                    SET default_transaction_read_only = on;
                    """
                ).format(

                    sql.Identifier(
                        READONLY_ROLE
                    )
                )
            )


            # ------------------------------------------------
            # Recreate application data table
            # ------------------------------------------------

            cursor.execute(
                f"""
                DROP TABLE IF EXISTS {TARGET_TABLE};

                CREATE TABLE {TARGET_TABLE} (

                    record_id BIGSERIAL
                        PRIMARY KEY,

                    federal_organization TEXT,

                    fiscal_year TEXT,

                    facility TEXT,

                    address TEXT,

                    city TEXT,

                    province TEXT,

                    postal_code TEXT,

                    building_floor_area_m2
                        NUMERIC,

                    electricity_conventional_kwh
                        NUMERIC,

                    electricity_clean_kwh
                        NUMERIC,

                    electricity_total_kwh
                        NUMERIC,

                    natural_gas_m3
                        NUMERIC,

                    propane_l
                        NUMERIC,

                    diesel_l
                        NUMERIC,

                    district_hot_water_gj
                        NUMERIC,

                    district_steam_gj
                        NUMERIC,

                    emissions_electricity_t
                        NUMERIC,

                    emissions_stationary_fuels_t
                        NUMERIC,

                    emissions_district_energy_t
                        NUMERIC
                );
                """
            )


            # ------------------------------------------------
            # Load records
            # ------------------------------------------------

            insert_sql = f"""
            INSERT INTO {TARGET_TABLE} (

                federal_organization,
                fiscal_year,
                facility,
                address,
                city,
                province,
                postal_code,

                building_floor_area_m2,

                electricity_conventional_kwh,

                electricity_clean_kwh,

                electricity_total_kwh,

                natural_gas_m3,

                propane_l,

                diesel_l,

                district_hot_water_gj,

                district_steam_gj,

                emissions_electricity_t,

                emissions_stationary_fuels_t,

                emissions_district_energy_t

            )

            VALUES (

                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s

            );
            """


            database_df = (

                dataframe
                .astype(object)
                .where(
                    pd.notnull(
                        dataframe
                    ),
                    None
                )
            )


            records = [

                tuple(row)

                for row
                in database_df.itertuples(
                    index=False,
                    name=None
                )
            ]


            cursor.executemany(
                insert_sql,
                records
            )


            # ------------------------------------------------
            # Permissions
            # ------------------------------------------------

            cursor.execute(
                """
                REVOKE CREATE
                ON SCHEMA public
                FROM PUBLIC;
                """
            )


            cursor.execute(

                sql.SQL(
                    """
                    GRANT USAGE
                    ON SCHEMA public
                    TO {};
                    """
                ).format(

                    sql.Identifier(
                        READONLY_ROLE
                    )
                )
            )


            cursor.execute(

                sql.SQL(
                    """
                    REVOKE ALL PRIVILEGES
                    ON ALL TABLES
                    IN SCHEMA public
                    FROM {};
                    """
                ).format(

                    sql.Identifier(
                        READONLY_ROLE
                    )
                )
            )


            cursor.execute(

                sql.SQL(
                    """
                    GRANT SELECT
                    ON {}
                    TO {};
                    """
                ).format(

                    sql.Identifier(
                        TARGET_TABLE
                    ),

                    sql.Identifier(
                        READONLY_ROLE
                    )
                )
            )


            connection.commit()


    print(
        "Database load and permissions: COMPLETE"
    )


def verify_database():

    readonly_url = os.environ[
        "READONLY_DATABASE_URL"
    ]


    with psycopg.connect(
        readonly_url
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM {TARGET_TABLE};
                """
            )


            count = (
                cursor.fetchone()[0]
            )


            cursor.execute(
                """
                SHOW default_transaction_read_only;
                """
            )


            readonly_default = (
                cursor.fetchone()[0]
            )


    print(
        "Rows visible to readonly_agent:",
        count
    )


    print(
        "default_transaction_read_only:",
        readonly_default
    )


    assert count == 535


    assert (
        str(
            readonly_default
        ).lower()
        in {
            "on",
            "true"
        }
    )


    print(
        "READ-ONLY VERIFICATION: PASS"
    )


if __name__ == "__main__":

    df = prepare_dataframe()

    assert (
        len(df)
        == 535
    )


    configure_database(
        df
    )


    verify_database()


    print(
        "REAL GOVERNMENT DATA LOADER: READY"
    )
