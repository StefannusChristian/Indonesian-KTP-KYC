from face_verification import FaceVerifier
from ocr import KTPOCR
from gui import GUI
# from bigquery import BigQuery
from local_db import LocalDB
import streamlit as st
import pandas as pd
import pymysql

def run_kyc():
    gui: GUI = GUI()
    gui.show_title()

    face_verifier: FaceVerifier = FaceVerifier(False)
    ocr: KTPOCR = KTPOCR(False)

    host: str = "localhost"
    username: str = "root"
    password: str = ""
    databasename: str = "kyc"
    tablename: str = "ktp_information"

    project_id: str = "dla-internship-program"
    dataset_id: str = "kyc_final_project"
    table_name: str = "extracted_ktp_informations"
    # bigquery: BigQuery = BigQuery(project_id, dataset_id, table_name)

    localDB: LocalDB = LocalDB(host, username, password, databasename, tablename)
    try:
        localDB.connect_to_database()
        localDB.create_ktp_information_table()
        ktp_image, image_to_verify, invalid_ktp = face_verifier.run()
        verify_button = gui.make_center_button("VERIFY KTP!")
        if verify_button:
            is_error,is_verify = face_verifier.verify_face(ktp_image, image_to_verify,False, invalid_ktp)
            if not is_error and is_verify:
                _, extracted_ktp_record = ocr.run(ktp_image,True)
                # bigquery.create_dataset(project_id,dataset_id)
                # df_to_generate_schema = pd.DataFrame([extracted_ktp_record])
                # bigquery.create_table(df_to_generate_schema)
                # bigquery.insert_ktp_information(extracted_ktp_record)
                localDB.insert_ktp_information(extracted_ktp_record)
    except pymysql.OperationalError as e:
        st.error(e.args[1])

if __name__ == "__main__":
    st.set_page_config(
        page_title="KYC",
        layout="wide",
        page_icon="../images/datalabs_logo/datalabs_logo_without_text.png"
    )
    run_kyc()