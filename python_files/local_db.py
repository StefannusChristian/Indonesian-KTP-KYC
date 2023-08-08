import pymysql

class LocalDB:
    def __init__(self, host, username, password, database, tablename):
        self.host = host
        self.username = username
        self.password = password
        self.database = database
        self.tablename = tablename
        self.connection = None
        self.cursor = None

    def connect_to_database(self):
        self.connection = pymysql.connect(
            host=self.host,
            user=self.username,
            password=self.password,
            database=self.database,
            autocommit=True
        )
        self.cursor = self.connection.cursor()

    def create_ktp_information_table(self):
        ktp_information_table_query = f"""
        CREATE TABLE IF NOT EXISTS {self.tablename} (
            Provinsi VARCHAR(255),
            KotaAtauKabupaten VARCHAR(255),
            NIK VARCHAR(255),
            Nama VARCHAR(255),
            TempatLahir VARCHAR(255),
            TanggalLahir VARCHAR(255),
            JenisKelamin VARCHAR(255),
            GolonganDarah VARCHAR(255),
            Alamat VARCHAR(255),
            RT VARCHAR(255),
            RW VARCHAR(255),
            KelurahanAtauDesa VARCHAR(255),
            Kecamatan VARCHAR(255),
            Agama VARCHAR(255),
            StatusPerkawinan VARCHAR(255),
            Pekerjaan VARCHAR(255),
            Kewarganegaraan VARCHAR(255),
            BerlakuHingga VARCHAR(255)
        );
        """

        self.cursor.execute(ktp_information_table_query)

    def insert_ktp_information(self, json_data: dict):
        try:
            # Check if the exact same NIK already exists in the table
            sql_query = f"SELECT COUNT(*) FROM {self.tablename} WHERE NIK = %s"
            self.cursor.execute(sql_query, (json_data['NIK'],))
            num_rows = self.cursor.fetchone()[0]

            if num_rows == 0:  # If the NIK does not exist in the table, insert the data
                # Generate the SQL query with parameter placeholders
                columns = ', '.join(json_data.keys())
                values = ', '.join('%s' for _ in json_data.values())
                sql_query = f"INSERT INTO {self.tablename} ({columns}) VALUES ({values})"

                # Execute the query with the data from the JSON
                self.cursor.execute(sql_query, tuple(json_data.values()))

                # Commit the changes to the database
                self.connection.commit()
                print("Data inserted successfully!")
            else: print("Data with the same NIK already exists. Skipping insertion.")

        except Exception as e: print(f"Error: {e}")

    def close_connection(self): self.connection.close()