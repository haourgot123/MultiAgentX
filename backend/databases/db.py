import math
from collections import namedtuple
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Tuple, TypeVar

import sqlalchemy
from fastapi import Query
from loguru import logger
from pydantic.types import constr
from six import string_types
from sqlalchemy import String, and_, cast, event, inspect, not_, or_
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, joinedload, load_only, sessionmaker
from sqlalchemy.orm.base import InspectionAttr
from sqlalchemy.orm.relationships import RelationshipProperty
from sqlalchemy_filters import apply_filters, apply_pagination, apply_sort
from sqlalchemy_filters.exceptions import BadFilterFormat

from backend.config.settings import _settings
from backend.exceptions.model import InvalidJoinFieldException
from backend.utils.constants import Message

Base = declarative_base()
engine: Engine = create_engine(_settings.postgres.url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_utc_now():
    """Get current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


# Add event listeners for connection pool monitoring
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    try:
        logger.info(
            f"Database connection established. Pool size: {engine.pool.size()}, checked out: {engine.pool.checkedout()}"
        )
    except Exception as e:
        logger.error(f"Error in receive_connect event listener: {e}")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    try:
        logger.debug(
            f"Database connection checked out. Pool size: {engine.pool.size()}, checked out: {engine.pool.checkedout()}"
        )
    except Exception as e:
        logger.error(f"Error in receive_checkout event listener: {e}")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    try:
        logger.debug(
            f"Database connection checked in. Pool size: {engine.pool.size()}, checked out: {engine.pool.checkedout()}"
        )
    except Exception as e:
        logger.error(f"Error in receive_checkin event listener: {e}")


@event.listens_for(engine, "close")
def receive_close(dbapi_connection, connection_record):
    try:
        logger.info(
            f"Database connection closed. Pool size: {engine.pool.size()}, checked out: {engine.pool.checkedout()}"
        )
    except Exception as e:
        logger.error(f"Error in receive_close event listener: {e}")


@event.listens_for(engine, "invalidate")
def receive_invalidate(dbapi_connection, connection_record, exception):
    try:
        logger.error(
            f"Database connection invalidated due to error: {exception}. Pool size: {engine.pool.size()}, checked out: {engine.pool.checkedout()}"
        )
    except Exception as e:
        logger.error(f"Error in receive_invalidate event listener: {e}")


ModelType = TypeVar("ModelType", bound=Base)  # type: ignore
QueryStr = constr(pattern=r"^[ -~]+$", min_length=1)

BooleanFunction = namedtuple(
    "BooleanFunction", ("key", "sqlalchemy_fn", "only_one_arg")
)
BOOLEAN_FUNCTIONS = [
    BooleanFunction("or", or_, False),
    BooleanFunction("and", and_, False),
    BooleanFunction("not", not_, True),
]


def get_class_by_tablename(table_fullname: str):
    for c in Base.registry._class_registry.values():
        if hasattr(c, "__table__"):
            if c.__table__.fullname.lower() == table_fullname.lower():
                return c

    raise Exception(f"Incorrect tablename {table_fullname}")


def get_by_id(
    db_session: Session,
    table,
    id,
    join_fields=[],
    expected_fields=[],
    exclude_fields=[],
):
    query = db_session.query(table).filter(table.id == id)
    if join_fields:
        query = perform_join(table, query, join_fields=join_fields)
    if expected_fields:
        expected_attributes = [getattr(table, field) for field in expected_fields]
        query = query.options(load_only(*expected_attributes))
    if exclude_fields:
        all_field_names = [col.name for col in table.__table__.columns]
        fields = [f for f in all_field_names if f not in exclude_fields]
        attributes = [getattr(table, f) for f in fields]
        query = query.options(load_only(*attributes))

    return query.first()


def get_by_ids(
    db_session: Session,
    table,
    ids,
    expected_fields: list[str] = None,
    exclude_fields: list[str] = None,
    join_fields: list[str] = None,
):
    query = db_session.query(table).filter(table.id.in_(ids))

    if join_fields:
        query = perform_join(table, query, join_fields=join_fields)

    if expected_fields:
        expected_attributes = [getattr(table, field) for field in expected_fields]
        query = query.options(load_only(*expected_attributes))
    elif exclude_fields:
        all_field_names = [col.name for col in table.__table__.columns]
        fields = [f for f in all_field_names if f not in exclude_fields]
        attributes = [getattr(table, f) for f in fields]
        query = query.options(load_only(*attributes))

    return query.all()


def get_by_custom_field(db_session: Session, table, custom_field, value):
    return db_session.query(table).filter(custom_field=value).first()


def get_by_custom_ilike(db_session: Session, table, custom_field, value):
    return db_session.query(table).filter(custom_field.ilike(value)).first()


def get_by_filter(
    db_session: Session,
    table,
    joins: Optional[List[Tuple]] = None,
    filters: Optional[List] = None,
    orders: Optional[List] = None,
    expected_fields: Optional[List[str]] = None,  # For load_only
    select_fields: Optional[List] = None,  # For query(func.count(...), ...)
    options: Optional[List] = None,  # For selectinload, joinedload, etc.
    group_by: Optional[List] = None,
    having: Optional[List] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    distinct: bool = False,
    count_only: bool = False,
    first: bool = False,
    scalar: bool = False,
    all: bool = False,
):  # noqa: C901
    """
    Generic, flexible query builder for SQLAlchemy models.

    Returns:
        .scalar() if scalar=True
        .first() if first=True
        .count() if count_only=True
        Otherwise: .all()
    """

    filters = filters or []
    orders = orders or []
    options = options or []

    if scalar and first:
        raise ValueError("Cannot use both `scalar` and `first` at the same time")

    # SELECT clause
    if select_fields:
        query = db_session.query(*select_fields)
    else:
        query = db_session.query(table)

    # JOIN clause
    if joins:
        for join_args in joins:
            if len(join_args) == 2:
                model_to_join, on_clause = join_args
                query = query.join(model_to_join, on_clause)
            elif len(join_args) == 3:
                model_to_join, on_clause, isouter = join_args
                query = query.join(model_to_join, on_clause, isouter=isouter)
            else:
                raise TypeError(
                    "Each join must be a tuple of (Model, on_clause[, isouter])"
                )

    # WHERE clause
    if filters:
        query = query.filter(*filters)

    # load_only (only when not using select_fields)
    if expected_fields and not select_fields:
        attrs = [getattr(table, f) for f in expected_fields]
        query = query.options(load_only(*attrs))

    # ORM loading options
    if options:
        query = query.options(*options)

    # GROUP BY and HAVING
    if group_by:
        query = query.group_by(*group_by)
    if having:
        query = query.having(*having)

    # ORDER BY
    if orders:
        query = query.order_by(*orders)

    # DISTINCT, LIMIT, OFFSET
    if distinct:
        query = query.distinct()
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    # RETURN types
    if count_only:
        return query.count()
    if scalar:
        return query.scalar()
    if first:
        return query.first()
    if all:
        return query.all()
    return query


def update_by_id(db_session: Session, table, id, update_data: dict):
    db_session.query(table).filter(table.id == id).update(update_data)
    db_session.commit()


def insert_row(db_session: Session, obj_table):
    db_session.add(obj_table)
    db_session.commit()
    db_session.refresh(obj_table)
    return obj_table


def update_row(db_session: Session, obj_table, obj_table_in):
    update_data = obj_table_in.dict(exclude_none=True)

    for field in update_data:
        setattr(obj_table, field, update_data[field])

    db_session.commit()
    db_session.refresh(obj_table)
    return obj_table


def delete_row(db_session: Session, obj_table):
    db_session.delete(obj_table)
    db_session.commit()
    return {"message": Message.DELETED_SUCCESSFULLY}


def delete_multi_rows(db_session: Session, table, custom_field, value):
    db_session.query(table).filter(custom_field == value).delete()
    db_session.commit()
    return {"message": Message.DELETED_SUCCESSFULLY}


def get_count(
    db_session: Session, table, filters: List = [], expected_fields: list[str] = None
):
    """Get count of records with optional filters and field selection."""
    query = db_session.query(table)
    if filters:
        query = query.filter(*filters)
    if expected_fields:
        expected_attributes = [getattr(table, field) for field in expected_fields]
        query = query.options(load_only(*expected_attributes))
    return query.count()


def get_by_name(
    db_session: Session, table, name: str, expected_fields: list[str] = None
):
    """Get record by name field with optional field selection."""
    query = db_session.query(table).filter(table.name == name)
    if expected_fields:
        expected_attributes = [getattr(table, field) for field in expected_fields]
        query = query.options(load_only(*expected_attributes))
    return query.first()


def get_all(
    db_session: Session,
    table,
    expected_fields: list[str] = None,
    exclude_fields: list[str] = None,
    orders: List = [],
):
    """Get all records with optional field selection and ordering."""
    query = db_session.query(table)
    if expected_fields:
        expected_attributes = [getattr(table, field) for field in expected_fields]
        query = query.options(load_only(*expected_attributes))
    elif exclude_fields:
        all_field_names = [col.name for col in table.__table__.columns]
        fields = [f for f in all_field_names if f not in exclude_fields]
        attributes = [getattr(table, f) for f in fields]
        query = query.options(load_only(*attributes))
    if orders:
        query = query.order_by(*orders)
    return query.all()


# Build Search, sort and filter common
def common_parameters(
    db_session: Session,
    page: int = Query(1, gt=0, lt=2147483647),
    items_per_page: int = Query(10, alias="itemsPerPage", gt=-2, lt=2147483647),
    filter_spec: str = Query("[]", alias="filterBy"),
    sort_by: List[str] = Query([], alias="sortBy"),
    descending: List[bool] = Query([], alias="descending"),
    query_str: QueryStr = Query("", alias="q"),  # type: ignore
    join_attrs: List[str] = Query([], alias="join"),
    search_fields: List[str] = Query([], alias="queryFields"),
):
    import json

    filter_spec = json.loads(filter_spec)
    return {
        "db_session": db_session,
        "page": page,
        "items_per_page": items_per_page,
        "query_str": query_str,
        "filter_spec": filter_spec,
        "sort_by": sort_by,
        "descending": descending,
        "join_attrs": join_attrs,
        "search_fields": search_fields,
    }


def get_relationship_fields(model):
    mapper = inspect(model)
    relationship_fields = {}
    for prop in mapper.attrs:
        if isinstance(prop, RelationshipProperty):
            relationship_fields[prop.key] = prop
            # relationship_fields.append((prop.key, prop))
    return relationship_fields


def perform_join(model_type: ModelType, query, join_fields=[]):
    for join_field in join_fields:
        join_field = join_field.strip()
        if join_field:
            if join_field in get_relationship_fields(model_type):
                query = query.options(joinedload(getattr(model_type, join_field)))
            else:
                raise InvalidJoinFieldException(
                    message=f"Invalid join field {join_field}"
                )

    return query


def filter_valid_fields(filter_spec, model):
    """
    Filters and validates fields in the filter specification based on the provided model,
    ensuring the model key is included in each filter.

    Args:
        filter_spec (List[dict]): The filter specifications to validate.
        model (Base): The SQLAlchemy model class.

    Returns:
        List[dict]: The filtered and validated filter specification with models included.
    """

    def process_filter(item, current_model):
        # Get valid columns for the current model
        valid_columns = {column.name for column in current_model.__table__.columns}

        # Handle logical structures (and, or)
        if isinstance(item, dict):
            if "or" in item:
                filtered_or = [
                    process_filter(f, current_model)
                    for f in item["or"]
                    if process_filter(f, current_model)
                ]
                if filtered_or:
                    return {"or": filtered_or}

            if "and" in item:
                filtered_and = [
                    process_filter(f, current_model)
                    for f in item["and"]
                    if process_filter(f, current_model)
                ]
                if filtered_and:
                    return {"and": filtered_and}

            # Handle individual filters with "field"
            if "field" in item and item["field"] in valid_columns:
                # Add the model key to the filter
                return {**item, "model": current_model.__tablename__}

        # If the item is invalid, return None
        return None

    # Process the list of filters and remove invalid entries
    return [process_filter(f, model) for f in filter_spec if process_filter(f, model)]


def generate_ilike_filters(model_cls, query_str, search_fields=None):
    partial_terms = [f"%{term}%" for term in query_str.split()]
    ilike_filters = []

    # Determine searchable columns: if search_fields provided, use those directly
    columns_to_search = (
        search_fields
        if search_fields
        else [
            column_name
            for column_name, column in model_cls.__table__.columns.items()
            if not isinstance(column.type, sqlalchemy.Enum)
            and isinstance(column.type, (sqlalchemy.String, sqlalchemy.Text))
        ]
    )
    for column_name in columns_to_search:
        column_attr = getattr(model_cls, column_name, None)
        if not column_attr:
            continue
        # Cast non-string fields to string for ILIKE compatibility
        is_string_type = isinstance(
            model_cls.__table__.columns[column_name].type,
            (sqlalchemy.String, sqlalchemy.Text),
        )
        for term in partial_terms:
            if is_string_type:
                ilike_filters.append(column_attr.ilike(term))
            else:
                ilike_filters.append(cast(column_attr, String).ilike(term))

    return or_(*ilike_filters) if ilike_filters else None


def search_filter_sort_paginate(
    db_session: Session,
    model,
    query_str: Optional[str] = None,
    filter_spec: Optional[List[dict]] = None,
    page: int = 1,
    items_per_page: int = 5,
    sort_by: Optional[List[str]] = None,
    descending: Optional[List[bool]] = None,
    join_attrs: Optional[List[str]] = None,
    query=None,
    search_fields: Optional[List[str]] = None,
    expected_fields: Optional[List[str]] = None,
):
    model_cls = get_class_by_tablename(model)
    query = query or db_session.query(model_cls)

    if query_str:
        ilike_filters = generate_ilike_filters(model_cls, query_str, search_fields)
        query = query.filter(ilike_filters)

    if filter_spec:
        filter_spec = filter_valid_fields(filter_spec, model_cls)

    valid_columns = {column.name for column in model_cls.__table__.columns}
    if sort_by:
        valid_sort_indices = [
            index for index, field in enumerate(sort_by) if field in valid_columns
        ]
        sort_by = [sort_by[i] for i in valid_sort_indices]
        descending = [descending[i] for i in valid_sort_indices]

    query = join_required_attrs(query, model_cls, join_attrs)
    query = perform_join(model_cls, query, join_fields=join_attrs)

    if filter_spec:
        filter_spec = build_filters_boolean(model, filter_spec)
        query = apply_filters(query, filter_spec)

    if sort_by:
        sort_spec = create_sort_spec(model, sort_by, descending)
        query = apply_sort(query, sort_spec)

    if expected_fields:
        column_fields = []
        relationship_fields = []

        for field in expected_fields:
            if hasattr(model_cls, field):  # Ensure field exists
                attr = getattr(model_cls, field)

                if isinstance(attr, InspectionAttr) and hasattr(attr, "property"):
                    if hasattr(attr.property, "columns"):  # Regular column
                        column_fields.append(field)
                    else:  # Relationship field (e.g., roles)
                        relationship_fields.append(field)

        if column_fields:
            query = query.options(
                load_only(*[getattr(model_cls, field) for field in column_fields])
            )

        for rel_field in relationship_fields:
            query = query.options(joinedload(getattr(model_cls, rel_field)))

    if items_per_page < 0:
        items_per_page = None

    query, pagination = apply_pagination(
        query, page_number=page, page_size=items_per_page
    )

    total_page = 1
    if items_per_page:
        total_page = math.ceil(pagination.total_results / items_per_page)
    next_page = page + 1 if page < total_page else -1
    has_more = next_page != -1
    data = query.all()

    return {
        "object": model,
        "total_item": pagination.total_results,
        "total_page": total_page,
        "has_more": has_more,
        "next_page": next_page,
        "data": data,
    }


def join_required_attrs(query, model, join_attrs):
    if not join_attrs:
        return query

    for attr in join_attrs:
        query = query.join(getattr(model, attr), isouter=True)

    return query


def create_sort_spec(model, sort_by, descending):
    """Creates sort_spec."""
    sort_spec = []
    if sort_by and descending:
        for field, direction in zip(sort_by, descending):
            direction = "desc" if direction else "asc"
            sort_spec.append({"model": model, "field": field, "direction": direction})

    return sort_spec


def build_filters_boolean(model, filter_spec):
    """Builds a filter spec."""

    for item in filter_spec:
        if isinstance(item, dict):
            is_bool = False
            for boolean_function in BOOLEAN_FUNCTIONS:
                if boolean_function.key in item:
                    is_bool = True
                    fn_args = item[boolean_function.key]

                    if not _is_iterable_filter(fn_args):
                        raise BadFilterFormat(
                            "`{}` value must be an iterable across the function "
                            "arguments".format(boolean_function.key)
                        )

                    for fn_arg in fn_args:
                        fn_arg["model"] = model
                    item[boolean_function.key] = fn_args
            if not is_bool:
                item["model"] = model
    return filter_spec


def _is_iterable_filter(filter_spec):
    """`filter_spec` may be a list of nested filter specs, or a dict."""
    return isinstance(filter_spec, Iterable) and not isinstance(
        filter_spec, (string_types, dict)
    )


def safe_sort_key(value):
    """Ensure None and empty values are handled correctly."""
    return (
        value is None,
        isinstance(value, str),
        isinstance(value, datetime) and value.timestamp(),
        value,
    )
