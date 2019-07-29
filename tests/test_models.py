from unittest import TestCase
from shutil import rmtree
import logging
import sqlite3
import pytest

from piicatcher.orm.models import *
from piicatcher.db.explorer import Explorer, SqliteExplorer
from piicatcher.db.metadata import Schema, Table, Column
from piicatcher.piitypes import PiiTypes
from piicatcher.orm.models import Store

logging.basicConfig(level=logging.DEBUG)


@pytest.mark.skip
class TestCreateTables(TestCase):
    sqlite_conn = 'file::memory:?cache=shared'

    def setUp(self):
        init_test(str(self.sqlite_conn))
        self.explorer = SqliteExplorer(str(self.sqlite_conn))

    def tearDown(self):
        self.explorer.close_connection()
        model_db_close()

    def test_schemas_exist(self):
        self.assertEqual(1, len(self.explorer.get_schemas()))

    def test_tables_exist(self):
        schema = self.explorer.get_schemas()[0]

        self.assertEqual(["dbcolumns", "dbschemas", "dbtables"],
                         [t.get_name() for t in schema.get_tables()])


class MockExplorer(Explorer):
    def _open_connection(self):
        pass

    def _get_catalog_query(self):
        pass

    def _load_catalog(self):
        pass

    def set_schema(self, schema):
        self._schemas = [schema]


class TestStore(TestCase):
    sqlite_path = 'file::memory:?cache=shared'

    @classmethod
    def setUpClass(cls):
        init_test(cls.sqlite_path)
        schema = Schema("test_store")

        no_pii_table = Table("test_store", "no_pii")
        no_pii_a = Column("a")
        no_pii_b = Column("b")

        no_pii_table.add(no_pii_a)
        no_pii_table.add(no_pii_b)

        schema.add(no_pii_table)

        partial_pii_table = Table("test_store", "partial_pii")
        partial_pii_a = Column("a")
        partial_pii_a.add_pii_type(PiiTypes.PHONE)
        partial_pii_b = Column("b")

        partial_pii_table.add(partial_pii_a)
        partial_pii_table.add(partial_pii_b)

        schema.add(partial_pii_table)

        full_pii_table = Table("test_store", "full_pii")
        full_pii_a = Column("a")
        full_pii_a.add_pii_type(PiiTypes.PHONE)
        full_pii_b = Column("b")
        full_pii_b.add_pii_type(PiiTypes.ADDRESS)
        full_pii_b.add_pii_type(PiiTypes.LOCATION)

        full_pii_table.add(full_pii_a)
        full_pii_table.add(full_pii_b)

        schema.add(full_pii_table)

        explorer = MockExplorer()
        explorer.set_schema(schema)

        Store.save_schemas(explorer)

    @classmethod
    def tearDownClass(cls):
        model_db_close()

    def test_schema(self):
        conn = sqlite3.connect(self.sqlite_path)
        c = conn.cursor()
        c.execute('select * from dbschemas')
        self.assertEqual([(1, 'test_store')], list(c.fetchall()))
        c.close()

    def test_tables(self):
        conn = sqlite3.connect(self.sqlite_path)
        c = conn.cursor()
        c.execute('select * from dbtables order by id')
        self.assertEqual([(1, 'no_pii', 1), (2, 'partial_pii', 1), (3, 'full_pii', 1)],
                         list(c.fetchall()))
        c.close()

    def test_columns(self):
        conn = sqlite3.connect(self.sqlite_path)
        c = conn.cursor()
        c.execute('select * from dbcolumns where table_id in (1,2) order by id')
        self.assertEqual(
            [(1, 'a', '[]', 1),
             (2, 'b', '[]', 1),
             (3, 'a', '[{"__enum__": "PiiTypes.PHONE"}]', 2),
             (4, 'b', '[]', 2)], list(c.fetchall()))
        c.close()

