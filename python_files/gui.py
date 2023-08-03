##################################################
#                Import module                   #
##################################################

import streamlit as st

class GUI:
    def show_title(self):
        col1,col2 = st.columns(2)
        with col1: st.title("Know Your Customer Internship Final Project")
        with col2:  st.image("../images/datalabs_logo/datalabs_logo.png",use_column_width=True)

    def make_center_button(self, button_text):
        col1, col2, col3 , col4, col5 = st.columns(5)
        with col1: pass
        with col2: pass
        with col4: pass
        with col5: pass
        with col3 : return st.button(button_text, use_container_width=True)

    # Method to show error message
    def show_error(self,message): return st.error(message)

    # Method to show warning message
    def show_warning(self,message): return st.warning(message)

    # Method to show success message
    def show_success(self,message): return st.success(message)

    def show_error_in_face_verification(self, is_first):
        message = "Cannot find face in First Image. Please Upload Another Image With A Clear Face!" if is_first else "Cannot find face in Second Image. Please Upload Another Image With A Clear Face!"
        self.show_error(message)

