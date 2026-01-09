from backend.databases.sqldb_factory import SQLDBFactory
from backend.utils.constants import ResourceFactory


def get_db():
    return SQLDBFactory.create(ResourceFactory.SQL_DB.value)
