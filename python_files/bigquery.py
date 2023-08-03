from time import sleep
from IPython.display import display
from google.cloud import bigquery
import google.api_core.exceptions
from google.cloud.bigquery.schema import SchemaField
import pandas as pd
import os

# * pip install --upgrade google-cloud-bigquery

class BigQuery:
    def __init__(self, project_id: str, dataset_id: str, table_name: str):
        self.get_credentials()
        self.client = self.create_client()
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_name = table_name

    # * Export Google BigQuery Query Result As A DataFrame Using BigQuery API In Python

    def get_credentials(self):
        credential_path = "C:/Users/chris/Kuliah/Magang/belajar/bigquery/datalabs_key/dla-internship-program.json"
        print("Getting credentials...")
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path
        print("Get credentials success!")

    # * Construct Big Query Client
    def create_client(self):
        print("Creating Client...")
        client = bigquery.Client()
        print("Create client success!")
        return client

    def get_table_id(self): return f"{self.project_id}.{self.dataset_id}.{self.table_name}"

    def create_dataset(self, project_id: str, dataset_id: str):
        project_id = project_id
        dataset_id = f"{project_id}.{dataset_id}"

        client = self.client

        # * Construct a full Dataset object to send to the API.
        dataset = bigquery.Dataset(dataset_id)

        # * Make an API request.
        try:
            dataset = client.create_dataset(dataset, timeout=30)
            print(f"Dataset {project_id}.{dataset_id} is Successfully created!")

        except google.api_core.exceptions.Conflict:
            print(f"Failed to create Dataset {project_id}.{dataset_id} because it already exists.")

    def generate_bigquery_schema(self, df: pd.DataFrame):
        TYPE_MAPPING = {
            "i": "INTEGER",
            "u": "NUMERIC",
            "b": "BOOLEAN",
            "f": "FLOAT",
            "O": "STRING",
            "S": "STRING",
            "U": "STRING",
            "M": "TIMESTAMP",
        }

        schema = []

        for column, dtype in df.dtypes.items():
            val = df[column].iloc[0]
            mode = "REPEATED" if isinstance(val, list) else "NULLABLE"

            if isinstance(val, dict) or (mode == "REPEATED" and isinstance(val[0], dict)):
                fields = self.generate_bigquery_schema(pd.json_normalize(val))
            else:
                fields = ()

            type = "RECORD" if fields else TYPE_MAPPING.get(dtype.kind)
            schema.append(
                SchemaField(
                    name=column,
                    field_type=type,
                    mode=mode,
                    fields=fields,
                )
            )

        return schema

    def create_table(self,df: pd.DataFrame):
        # Construct a BigQuery client object.
        client = self.client
        table_id = self.get_table_id()
        schema = self.generate_bigquery_schema(df)
        print(schema)

        try:
            table = bigquery.Table(table_id, schema=schema)
            table = client.create_table(table)
            print(f"{self.table_name} has successfully been created!")

        except google.api_core.exceptions.Conflict:
            print(f"Failed to create {self.table_name} because it already exists.")

    def insert_ktp_information(self, row_to_insert):
        """
        Example:
        row_to_insert must be a single record (dictionary):
        {"Name": "John", "Age": 25, "City": "New York"}
        """
        client = self.client
        table_id = self.get_table_id()

        # Step 1: Check if the row_to_insert already exists in BigQuery
        query = f"SELECT COUNT(*) FROM {table_id} WHERE "
        conditions = [f"{field} = '{value}'" for field, value in row_to_insert.items()]
        query += " AND ".join(conditions)

        query_job = client.query(query)
        result = list(query_job)
        count = result[0][0]

        # Step 2: Insert the row_to_insert if it does not already exist
        if count == 0:
            errors = client.insert_rows_json(table_id, [row_to_insert])
            if errors == []: print("New row has been added")
            else: print(f"Encountered errors while inserting rows: {errors}")
        else: print("Row already exists in the table, not inserting.")

