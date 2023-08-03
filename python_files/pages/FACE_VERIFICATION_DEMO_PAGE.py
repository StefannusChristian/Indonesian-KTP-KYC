from face_verification import FaceVerifier
import streamlit as st

st.set_page_config(layout="wide")
face_verifier: FaceVerifier = FaceVerifier(True)
face_verifier.run_demo()