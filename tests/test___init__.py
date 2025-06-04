import csv
import unittest
from unittest import TestCase
import os
import logging
from tempfile import TemporaryFile, mkdtemp
from pandas.api.types import is_datetime64_ns_dtype, is_float_dtype, is_int64_dtype, is_object_dtype
from multiprocessing import Process

from enverus_developer_api import (
    DeveloperAPIv3,
    DirectAccessV2,
    DAQueryException,
    DAAuthException
)

LOG_LEVEL = logging.DEBUG
if os.environ.get("GITHUB_SHA"):
    LOG_LEVEL = logging.ERROR


def set_token_v2():
    if not os.environ.get("DIRECTACCESS_TOKEN"):
        os.environ["DIRECTACCESS_TOKEN"] = DirectAccessV2(
            client_id=os.environ.get("DIRECTACCESS_CLIENT_ID"),
            client_secret=os.environ.get("DIRECTACCESS_CLIENT_SECRET"),
            api_key=os.environ.get("DIRECTACCESS_API_KEY"),
        ).access_token
    return


def set_token_v3():
    if not os.environ.get("DIRECTACCESSV3_TOKEN"):
        os.environ["DIRECTACCESSV3_TOKEN"] = DeveloperAPIv3(
            secret_key=os.environ.get("DIRECTACCESSV3_API_KEY"),
            # url="https://api.dev.enverus.com/"
        ).access_token
    return


def create_developerapi_v3():
    return DeveloperAPIv3(
        secret_key=os.environ.get("DIRECTACCESSV3_API_KEY"),
        access_token=os.environ.get("DIRECTACCESSV3_TOKEN"),
        # url="https://api.dev.enverus.com/",
        retries=5,
        backoff_factor=10,
        log_level=LOG_LEVEL
    )


def create_directaccess_v2():
    return DirectAccessV2(
        api_key=os.environ.get("DIRECTACCESS_API_KEY"),
        client_id=os.environ.get("DIRECTACCESS_CLIENT_ID"),
        client_secret=os.environ.get("DIRECTACCESS_CLIENT_SECRET"),
        access_token=os.environ.get("DIRECTACCESS_TOKEN"),
        retries=5,
        backoff_factor=10,
        log_level=LOG_LEVEL
    )


def proc_query(dataset):
    v3 = create_developerapi_v3()
    resp = v3.query(dataset, deleteddate="null")
    next(resp)
    TestCase.assertTrue(resp)
    return


class TestEnverusDeveloperAPI(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        set_token_v3()
        cls.v3 = create_developerapi_v3()

        set_token_v2()
        cls.v2 = create_directaccess_v2()

    def test_missing_secret_key_v3(self):
        with self.assertRaises(DAAuthException):
            DeveloperAPIv3(secret_key=None, log_level=LOG_LEVEL)

    def test_query_v3(self):
        query = self.v3.query("casings", pagesize=10, deleteddate="null")
        records = list()
        for i, row in enumerate(query, start=1):
            # print(row)
            records.append(row)
            if i % 30 == 0:
                break
        self.assertTrue(len(records) > 0, "test_query_v3 records list empty")

    def test_query_v3_omit_header_next_link(self):
        query = self.v3.query("casings", pagesize=10, deleteddate="null", _headers={'X-Omit-Header-Next-Links': 'true'})
        records = list()
        for i, row in enumerate(query, start=1):
            records.append(row)
            if i % 30 == 0:
                break
        self.assertTrue(len(records) > 0, "test_query_v3 records list empty")

    def test_is_omit_header_next_link(self):
        is_omit_next_link = self.v3.is_omit_header_next_link(_headers={'X-Omit-Header-Next-Links': 'true'})
        self.assertTrue(is_omit_next_link, "test_is_omit_header_next_link should contain omit header")

        is_omit_next_link = self.v3.is_omit_header_next_link(_headers={'Omit-Header-Next-Links': 'true'})
        self.assertTrue(not is_omit_next_link, "test_is_omit_header_next_link should not contain omit header")

    def test_parse_links(self):
        links = self.v3.parse_links(
            {"next": "</economics?action=next&next_page=WellID+%3C+840600005436298&pagesize=50>; rel='next'"})
        self.assertTrue(links["next"]["url"], "/economics?action=next&next_page=WellID+%3C+840600005436298&pagesize=50")

    def test_docs_v3(self):
        docs = self.v3.docs("casings")
        self.assertTrue(docs)
        self.assertIsInstance(docs, list)

    def test_ddl_v3(self):
        ddl = self.v3.ddl("casings", database="pg")
        with TemporaryFile(mode="w+") as f:
            f.write(ddl)
            f.seek(0)
            for line in f:
                self.assertTrue(line.startswith("CREATE TABLE casings"))
                break

    def test_ddl_invalid_db_v3(self):
        with self.assertRaises(DAQueryException):
            self.v3.ddl("casings", database="invalid")

    def test_count_v3(self):
        count = self.v3.count("wells", updateddate="ge(2021-05-01)", StateProvince="in(TX,LA,WY)")
        self.assertIsNotNone(count)
        self.assertIsInstance(count, int)

   # def test_count_invalid_dataset_v3(self):
    #      with self.assertRaises(DADatasetException):
     #       self.v3.count("invalid")

    def test_token_refresh_v3(self):
        v3 = DeveloperAPIv3(
            secret_key=os.environ.get("DIRECTACCESSV3_API_KEY"),
            access_token="invalid",
            # url="https://api.dev.enverus.com/",
            retries=5,
            backoff_factor=10,
            log_level=LOG_LEVEL
        )

        invalid_token = v3.access_token
        count = v3.count("rigs", deleteddate="null")
        query = v3.query("rigs", pagesize=10000, deleteddate="null")
        self.assertTrue(len([x for x in query]) == count)
        self.assertTrue(invalid_token != v3.access_token)

    def test_csv_v3(self):
        tempdir = mkdtemp()
        path = os.path.join(tempdir, "rigs.csv")

        dataset = "rigs"
        options = dict(pagesize=10000, deleteddate="null")

        count = self.v3.count(dataset, **options)
        query = self.v3.query(dataset, **options)
        self.v3.to_csv(query, path, log_progress=True, delimiter=",", quoting=csv.QUOTE_MINIMAL)

        with open(path, mode="r") as f:
            reader = csv.reader(f)
            row_count = len([x for x in reader])
            self.assertTrue(row_count == (count + 1))

    def test_dataframe_v3(self):
        df = self.v3.to_dataframe("rigs", pagesize=1000, deleteddate="null")

        # Check index is set to API endpoint "primary keys"
        self.assertListEqual(df.index.names, ["CompletionID", "WellID"])

        # Check object dtypes
        self.assertTrue(is_object_dtype(df.API_UWI))
        self.assertTrue(is_object_dtype(df.ActiveStatus))

        # Check datetime64 dtypes
        self.assertTrue(is_datetime64_ns_dtype(df.DeletedDate))
        self.assertTrue(is_datetime64_ns_dtype(df.SpudDate))
        self.assertTrue(is_datetime64_ns_dtype(df.UpdatedDate))

        # Check Int64 dtypes
        self.assertTrue(is_int64_dtype(df.RatedWaterDepth))
        self.assertTrue(is_int64_dtype(df.RatedHP))

        # Check float dtypes
        self.assertTrue(is_float_dtype(df.RigLatitudeWGS84))
        self.assertTrue(is_float_dtype(df.RigLongitudeWGS84))

    def test_multiple_processes_v3(self):
        # Launch two child processes, one for rigs and one for casings

        procs = [
            Process(target=proc_query, kwargs=dict(dataset="rigs")),
            Process(target=proc_query, kwargs=dict(dataset="casings"))
        ]

        [x.start() for x in procs]
        [x.join() for x in procs]

    def test_enter_exit(self):
        with DeveloperAPIv3(secret_key=os.environ.get("DIRECTACCESSV3_API_KEY"),
                            access_token=os.environ.get("DIRECTACCESSV3_TOKEN")) as api:
            self.assertIsInstance(api, DeveloperAPIv3)
            self.assertIsNotNone(api.session)

        self.assertIsNone(api.session)

    # ******************** DirectAccessV2 Test Cases **********************

    def test_missing_client_id_v2(self):
        with self.assertRaises(DAAuthException):
            DirectAccessV2(client_id=None,
                           client_secret=os.environ.get("DIRECTACCESS_CLIENT_SECRET"),
                           log_level=LOG_LEVEL)

    def test_missing_client_secret_v2(self):
        with self.assertRaises(DAAuthException):
            DirectAccessV2(client_id=os.environ.get("DIRECTACCESS_CLIENT_ID"),
                           client_secret=None,
                           log_level=LOG_LEVEL)

    def test_query_v2(self):
        query = self.v2.query("rigs", pagesize=10, deleteddate="null")
        records = list()
        for i, row in enumerate(query, start=1):
            # print(row)
            records.append(row)
            if i % 30 == 0:
                break
        self.assertTrue(len(records) > 0, "test_query_v2 records list empty")


if __name__ == '__main__':
    unittest.main()
