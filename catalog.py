"""
SonoBot — Catalog Logic
Product search, category listing, and result formatting using the database layer.
"""

import logging
import os

import mysql.connector

from config import CATALOG_PROVIDER, JOOMLA_TABLE_PREFIX, CATALOG_LIST_LIMIT
from db import get_db_connection
from utils import normalize_text, normalize_search_key, extract_keywords, extract_product_keywords

logger = logging.getLogger("sonobot.catalog")

# ---------------------------------------------------------------------------
# Catalog Provider Helpers
# ---------------------------------------------------------------------------


def get_catalog_provider():
    return CATALOG_PROVIDER


def get_hikashop_prefix(cursor):
    if JOOMLA_TABLE_PREFIX:
        return JOOMLA_TABLE_PREFIX

    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_name LIKE %s
        LIMIT 1
        """,
        ("%\\_hikashop_product",),
    )
    row = cursor.fetchone()
    if not row:
        raise mysql.connector.Error(
            "Could not find a HikaShop product table in the configured database."
        )

    table_name = row["table_name"]
    return table_name[: -len("hikashop_product")]


# ---------------------------------------------------------------------------
# SQL Builders
# ---------------------------------------------------------------------------


def catalog_select_sql(cursor):
    """Returns the product query fields and table joins for the active catalog."""
    if get_catalog_provider() == "hikashop":
        prefix = get_hikashop_prefix(cursor)
        return f"""
            SELECT
                p.product_name AS name,
                p.product_description AS description,
                COALESCE(MIN(pr.price_value), 0) AS price,
                CASE
                    WHEN p.product_quantity < 0 THEN 999999
                    ELSE p.product_quantity
                END AS stock,
                COALESCE(
                    GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', '),
                    'Uncategorized'
                ) AS category
            FROM `{prefix}hikashop_product` p
            LEFT JOIN `{prefix}hikashop_price` pr
                ON pr.price_product_id = p.product_id
            LEFT JOIN `{prefix}hikashop_product_category` pc
                ON pc.product_id = p.product_id
            LEFT JOIN `{prefix}hikashop_category` c
                ON c.category_id = pc.category_id
            WHERE p.product_published = 1
              AND p.product_type = 'main'
        """

    return """
        SELECT name, description, price, stock, category
        FROM products
        WHERE 1 = 1
    """


def catalog_group_order_sql():
    if get_catalog_provider() == "hikashop":
        return " GROUP BY p.product_id, p.product_name, p.product_description, p.product_quantity ORDER BY category ASC, price ASC"

    return " ORDER BY category ASC, price ASC"


def catalog_search_condition_sql():
    if get_catalog_provider() == "hikashop":
        return "(p.product_name LIKE %s OR p.product_description LIKE %s OR c.category_name LIKE %s)"

    return "(name LIKE %s OR description LIKE %s OR category LIKE %s)"


# ---------------------------------------------------------------------------
# Product Queries
# ---------------------------------------------------------------------------


def search_database(user_message):
    """Searches the MySQL database for products matching keywords in the user's message."""
    keywords = extract_keywords(user_message)
    products = []

    try:
        with get_db_connection() as (_conn, cursor):
            base_query = catalog_select_sql(cursor)
            params = []

            if keywords:
                conditions = []
                for word in keywords:
                    conditions.append(catalog_search_condition_sql())
                    pattern = f"%{word}%"
                    params.extend([pattern, pattern, pattern])
                base_query += " AND (" + " OR ".join(conditions) + ")"

            query = base_query + catalog_group_order_sql() + " LIMIT %s"
            cursor.execute(query, [*params, 10 if keywords else 5])
            products = cursor.fetchall()

            if keywords and not products:
                query = catalog_select_sql(cursor) + catalog_group_order_sql() + " LIMIT %s"
                cursor.execute(query, [3])
                products = cursor.fetchall()

    except mysql.connector.Error as err:
        logger.error("Database Error in search_database: %s", err)

    return products


def fetch_product_matches(user_message, limit=8):
    """Finds closest product-name matches before sending the question to AI."""
    keywords = [kw for kw in extract_product_keywords(user_message) if kw]
    if not keywords:
        return []

    try:
        with get_db_connection() as (_conn, cursor):
            if get_catalog_provider() == "hikashop":
                prefix = get_hikashop_prefix(cursor)
                relevance_parts = []
                where_parts = []
                relevance_params = []
                where_params = []

                for keyword in keywords:
                    pattern = f"%{keyword}%"
                    relevance_parts.append(
                        """
                        MAX(
                            CASE
                                WHEN LOWER(p.product_name) LIKE %s THEN 5
                                WHEN LOWER(c.category_name) LIKE %s THEN 2
                                WHEN LOWER(p.product_description) LIKE %s THEN 1
                                ELSE 0
                            END
                        )
                        """
                    )
                    relevance_params.extend([pattern, pattern, pattern])
                    where_parts.append(
                        "(LOWER(p.product_name) LIKE %s OR LOWER(c.category_name) LIKE %s OR LOWER(p.product_description) LIKE %s)"
                    )
                    where_params.extend([pattern, pattern, pattern])

                query = f"""
                    SELECT
                        p.product_name AS name,
                        p.product_description AS description,
                        COALESCE(MIN(pr.price_value), 0) AS price,
                        CASE
                            WHEN p.product_quantity < 0 THEN 999999
                            ELSE p.product_quantity
                        END AS stock,
                        COALESCE(
                            GROUP_CONCAT(DISTINCT c.category_name ORDER BY c.category_name SEPARATOR ', '),
                            'Uncategorized'
                        ) AS category,
                        ({' + '.join(relevance_parts)}) AS relevance_score
                    FROM `{prefix}hikashop_product` p
                    LEFT JOIN `{prefix}hikashop_price` pr
                        ON pr.price_product_id = p.product_id
                    LEFT JOIN `{prefix}hikashop_product_category` pc
                        ON pc.product_id = p.product_id
                    LEFT JOIN `{prefix}hikashop_category` c
                        ON c.category_id = pc.category_id
                    WHERE p.product_published = 1
                      AND p.product_type = 'main'
                      AND ({' OR '.join(where_parts)})
                    GROUP BY p.product_id, p.product_name, p.product_description, p.product_quantity
                    HAVING relevance_score > 0
                    ORDER BY relevance_score DESC, category ASC, price ASC
                    LIMIT %s
                """
                cursor.execute(query, [*relevance_params, *where_params, limit])
                return cursor.fetchall()

            # Sample / generic products table
            where_parts = []
            relevance_params = []
            where_params = []
            relevance_parts = []
            for keyword in keywords:
                pattern = f"%{keyword}%"
                relevance_parts.append(
                    """
                    CASE
                        WHEN LOWER(name) LIKE %s THEN 5
                        WHEN LOWER(category) LIKE %s THEN 2
                        WHEN LOWER(description) LIKE %s THEN 1
                        ELSE 0
                    END
                    """
                )
                relevance_params.extend([pattern, pattern, pattern])
                where_parts.append(
                    "(LOWER(name) LIKE %s OR LOWER(category) LIKE %s OR LOWER(description) LIKE %s)"
                )
                where_params.extend([pattern, pattern, pattern])

            query = f"""
                SELECT name, description, price, stock, category,
                       ({' + '.join(relevance_parts)}) AS relevance_score
                FROM products
                WHERE {' OR '.join(where_parts)}
                ORDER BY relevance_score DESC, category ASC, price ASC
                LIMIT %s
            """
            cursor.execute(query, [*relevance_params, *where_params, limit])
            return cursor.fetchall()

    except mysql.connector.Error as err:
        logger.error("Database Error in fetch_product_matches: %s", err)
        return []


def fetch_categories():
    """Returns product categories that actually contain published catalog products."""
    try:
        with get_db_connection() as (_conn, cursor):
            if get_catalog_provider() == "hikashop":
                prefix = get_hikashop_prefix(cursor)
                cursor.execute(
                    f"""
                    SELECT DISTINCT c.category_name AS name
                    FROM `{prefix}hikashop_category` c
                    INNER JOIN `{prefix}hikashop_product_category` pc
                        ON pc.category_id = c.category_id
                    INNER JOIN `{prefix}hikashop_product` p
                        ON p.product_id = pc.product_id
                    WHERE p.product_published = 1
                      AND p.product_type = 'main'
                      AND c.category_name IS NOT NULL
                      AND c.category_name <> ''
                    ORDER BY c.category_name ASC
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT DISTINCT category AS name
                    FROM products
                    WHERE category IS NOT NULL AND category <> ''
                    ORDER BY category ASC
                    """
                )

            return [str(row["name"]).strip() for row in cursor.fetchall() if str(row["name"]).strip()]

    except mysql.connector.Error as err:
        logger.error("Database Error in fetch_categories: %s", err)
        return []


def fetch_products_by_category(category, limit=100):
    """Fetches products belonging to a specific category."""
    if not category:
        return []

    try:
        with get_db_connection() as (_conn, cursor):
            if get_catalog_provider() == "hikashop":
                prefix = get_hikashop_prefix(cursor)
                query = f"""
                    {catalog_select_sql(cursor)}
                      AND EXISTS (
                          SELECT 1
                          FROM `{prefix}hikashop_product_category` pc_filter
                          INNER JOIN `{prefix}hikashop_category` c_filter
                              ON c_filter.category_id = pc_filter.category_id
                          WHERE pc_filter.product_id = p.product_id
                            AND c_filter.category_name = %s
                      )
                    {catalog_group_order_sql()}
                    LIMIT %s
                """
                cursor.execute(query, [category, limit])
                return cursor.fetchall()

            query = (
                catalog_select_sql(cursor)
                + " AND category = %s"
                + catalog_group_order_sql()
                + " LIMIT %s"
            )
            cursor.execute(query, [category, limit])
            return cursor.fetchall()

    except mysql.connector.Error as err:
        logger.error("Database Error in fetch_products_by_category: %s", err)
        return []


def fetch_products(where_clause="", params=None, limit=10):
    """Fetches catalog products for direct, fast answers that do not need AI."""
    params = params or []

    try:
        with get_db_connection() as (_conn, cursor):
            query = catalog_select_sql(cursor)

            if get_catalog_provider() == "hikashop":
                having_clause = ""
                if "stock > 0" in where_clause:
                    query += " AND p.product_quantity != 0"
                if "price BETWEEN" in where_clause:
                    having_clause = " HAVING price BETWEEN %s AND %s"
                elif "price <=" in where_clause:
                    having_clause = " HAVING price <= %s"
                elif "price >=" in where_clause:
                    having_clause = " HAVING price >= %s"
                query += catalog_group_order_sql().replace(
                    " ORDER BY", f"{having_clause} ORDER BY"
                )
            else:
                if where_clause:
                    query += f" AND {where_clause}"
                query += catalog_group_order_sql()

            if limit:
                query += " LIMIT %s"
                params = [*params, limit]

            cursor.execute(query, params)
            return cursor.fetchall()

    except mysql.connector.Error as err:
        logger.error("Database Error in fetch_products: %s", err)
        return None


# ---------------------------------------------------------------------------
# Formatting Helpers
# ---------------------------------------------------------------------------


def _stock_label(product):
    stock_count = int(product["stock"] or 0)
    if stock_count >= 999999:
        return "disponible"
    elif stock_count > 0:
        return f"{stock_count} en stock"
    else:
        return "rupture de stock"


def format_product_list(products, intro, group_by_category=False):
    if products is None:
        return "I cannot read the HikaShop catalog yet. Please check DB_NAME and JOOMLA_TABLE_PREFIX in the .env file."

    if not products:
        return "I couldn't find matching products in the catalog right now."

    def product_line(product):
        return f"- {str(product['name']).strip()}: {product['price']:.2f} MAD ({_stock_label(product)})"

    lines = [intro]

    if group_by_category:
        grouped_products = {}
        for product in products:
            categories = [
                c.strip()
                for c in (product.get("category") or "Uncategorized").split(",")
            ]
            category = categories[0] if categories and categories[0] else "Uncategorized"
            grouped_products.setdefault(category, []).append(product)

        for category, category_products in grouped_products.items():
            lines.append(f"\n**{category}** :")
            for product in category_products:
                lines.append(product_line(product))
    else:
        for product in products:
            category = product.get("category") or "Uncategorized"
            lines.append(f"{product_line(product)} - {category}")

    return "\n".join(lines)


def format_category_list(categories):
    if not categories:
        return "Je n'arrive pas à lire les catégories du catalogue pour le moment."

    lines = ["Voici les catégories qui existent dans le catalogue :"]
    lines.extend(f"- {category}" for category in categories)
    return "\n".join(lines)


def find_requested_category(user_message, categories):
    message_key = normalize_search_key(user_message)
    matches = [
        category
        for category in categories
        if normalize_search_key(category) and normalize_search_key(category) in message_key
    ]
    if not matches:
        return None

    return max(matches, key=lambda category: len(normalize_search_key(category)))
