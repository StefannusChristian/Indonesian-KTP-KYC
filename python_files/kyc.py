from face_verification import FaceVerifier
from ocr import KTPOCR
from gui import GUI
from bigquery import BigQuery
import streamlit as st
import pandas as pd

def run_kyc():
    gui = GUI()
    gui.show_title()
    face_verifier = FaceVerifier(False)
    ocr = KTPOCR(False)
    project_id = "dla-internship-program"
    dataset_id = "kyc_final_project"
    table_name = "extracted_ktp_informations"
    bigquery = BigQuery(project_id, dataset_id, table_name)
    ktp_image, image_to_verify, invalid_ktp = face_verifier.run()
    verify_button = gui.make_center_button("VERIFY KTP!")
    if verify_button:
        is_error,is_verify = face_verifier.verify_face(ktp_image, image_to_verify,False, invalid_ktp)
        if not is_error and is_verify:
            df, extracted_ktp_record = ocr.run(ktp_image,True)
            bigquery.create_dataset(project_id,dataset_id)
            df_to_generate_schema = pd.DataFrame([extracted_ktp_record])
            bigquery.create_table(df_to_generate_schema)
            bigquery.insert_ktp_information(extracted_ktp_record)

if __name__ == "__main__":
    st.set_page_config(
        page_title="KYC",
        layout="wide",
        page_icon="../images/datalabs_logo/datalabs_logo_without_text.png"
    )
    run_kyc()