import streamlit as st  # Streamlit library for building interactive web applications
from mtcnn.mtcnn import MTCNN  # MTCNN for face detection
# PIL library for image processing
from PIL import ExifTags
from PIL import Image
from numpy import asarray  # numerical operations
from keras_vggface.utils import preprocess_input  # Preprocessing utility for VGGFace
# Import modules for face recognition
from scipy.spatial.distance import cosine  # SciPy for calculating cosine similarity
from keras_vggface.vggface import VGGFace  # VGGFace model for face recognition
from gui import GUI
import os
from keras.models import load_model
import cv2
import numpy as np

class FaceVerifier:
    #########################################################
    #                    Constructor                         #m
    #########################################################
    def __init__(self, is_demo: bool):
        self.face_not_found_error_msg = "Face Not Detected! Please Upload Another Image With A Clear Face!"
        self.empty_image_msg = "Please Upload An Image!"
        self.empty_ktp_image_msg = "Please Upload KTP Image!"
        self.empty_image_to_verify_msg = "Please Upload Image To Verify!"
        self.empty_ktp_file = "Please Upload Your KTP As Image!"
        self.invalid_ktp_msg = "Please Upload A Valid KTP Image!"
        self.face_verification_threshold = 0.5
        self.gui = GUI()
        self.valid_image_extensions = ["jpg", "jpeg", "png"]
        self.pretrained_ktp_classifier_model = "../ktp classifier.h5/"
        self.loaded_model = load_model(self.pretrained_ktp_classifier_model)
        if not is_demo: self.checkbox = st.checkbox("Stop Camera Input")
        else:
            col1,col2 = st.columns(2)
            with col1: st.title("Face Verification Demo")
            with col2: st.image("../images/other_images/identity_verification_image.jpeg")

        # Initialize the MTCNN face detection model
        self.face_detector = MTCNN()
        self.base_ktp_image_local_path = "../ktp_classification/ktp_images/all_images/"

    def fix_image_orientation(self, image):
        if hasattr(image, '_getexif'):
            exif = image._getexif()
            if exif is not None:
                for tag, value in exif.items():
                    if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                        if value == 3: image = image.rotate(180, expand=True)
                        elif value == 6: image = image.rotate(270, expand=True)
                        elif value == 8: image = image.rotate(90, expand=True)
        return image

    #########################################################
    #                 Extract Face Method                   #
    #########################################################

    '''
    extracts and resizes the face region from an input image using the MTCNN (Multi-Task Cascaded Convolutional Neural Networks) face detection model
    '''

    def extract_face(self, file):
        # Convert the file to pixels (numpy array)
        pixels = asarray(file)
        # st.write(pixels)

        # Detect faces in the image using the MTCNN model
        try:
            results = self.face_detector.detect_faces(pixels)

            # Retrieve the coordinates and dimensions of the bounding box around the first detected face
            x1, y1, width, height = results[0]["box"]

            # Calculate the coordinates of the bottom-right corner of the bounding box
            x2, y2 = x1 + width, y1 + height

            # Extract the face region from the image based on the bounding box coordinates
            face = pixels[y1:y2, x1:x2]

            # Create a PIL Image object from the face region
            image = Image.fromarray(face)

            # Resize the image to 224x224 pixels
            '''
            why 224x224 px?
            1. Standardization: ensures that all images being processed have the same size

            2. Model Compatibility: Many pre-trained deep learning models have been trained on image datasets with an input size of 224x224

            3. Computational Efficiency: faster training and inference times

            4. Sufficient Information: retains sufficient information for many computer vision tasks. The downscaled image generally preserves important features and patterns necessary for tasks like face recognition, object detection, and image classification.
            '''
            image = image.resize((224, 224))

            # Convert the resized image back to a numpy array
            face_array = asarray(image)

            # Return the numpy array representing the resized face
            return face_array

        except: return None

    def verify_face(self, image1, image2, is_demo: bool, invalid_ktp: bool):
        is_error, is_verify = False, False
        if (image1 is not None) and (image2 is not None):
            col1, col2 = st.columns(2)
            image1 = Image.open(image1)
            image2 = Image.open(image2)

            image1 = self.fix_image_orientation(image1)
            image2 = self.fix_image_orientation(image2)

            detected_face_1 = self.extract_face(image1)
            detected_face_2 = self.extract_face(image2)

            if detected_face_1 is None: self.gui.show_error_in_face_verification(True)
            if detected_face_2 is None: self.gui.show_error_in_face_verification(False)

            faces = [detected_face_1, detected_face_2]
            if all(face is not None for face in faces) and not invalid_ktp:
                subheader1 = "KTP Image"
                subheader2 = "Image To Verify"
                if is_demo:
                    subheader1 = "Image 1"
                    subheader2 = "Image 2"
                with col1:
                    st.subheader(subheader1)
                    st.image(image1)
                with col2:
                    st.subheader(subheader2)
                    st.image(image2)

                st.header("Detected Faces")
                col3, col4 = st.columns(2)
                with col3: st.image(detected_face_1)
                with col4: st.image(detected_face_2)

                samples = asarray(faces, dtype="float32")
                samples = preprocess_input(samples, version=2)
                model = VGGFace(model="resnet50", include_top=False, input_shape=(224, 224, 3), pooling="avg")
                embeddings = model.predict(samples)

                score = cosine(embeddings[0], embeddings[1])
                percent_match = (1 - score) * 100

                col5, col6 = st.columns(2)
                with col5:
                    if score <= self.face_verification_threshold:
                        st.success("> FACE MATCH! (%.4f <= %.1f)" % (score, self.face_verification_threshold))
                        is_verify = True
                        if not is_demo: st.balloons()
                    else:
                        st.error("> FACE UNMATCH! (%.4f > %.1f)" % (score, self.face_verification_threshold))
                if not is_verify and not is_demo: st.error("OCR IS NOT RUN BECAUSE FACE IS UNMATCH!")

                with col6: st.info("> Face similarity: %.2f%%" % percent_match)

        else:
            col1,col2 = st.columns(2)
            with col1:
                if invalid_ktp:
                    self.gui.show_warning(self.invalid_ktp_msg)
                elif image1 is None:
                    self.gui.show_warning(self.empty_ktp_image_msg)

            with col2: self.gui.show_warning(self.empty_image_to_verify_msg)
            if image1 is None or image2 is None: is_error = True
        return is_error, is_verify

    def preprocess_image(self, image_path):
        image = cv2.imread(image_path)
        image = cv2.resize(image, (32, 32))
        image = image / 255.0
        image = np.expand_dims(image, axis=0)
        return image

    def is_image_ktp(self, test_image_path):
        image_to_test = self.preprocess_image(test_image_path)
        predicted_probabilities = self.loaded_model.predict(image_to_test)
        predicted_class = np.argmax(predicted_probabilities)
        threshold = 0.5
        predicted_class = 1 if predicted_probabilities[0, 0] > threshold else 0
        return True if predicted_class is 1 else False

    def run(self):
        invalid_ktp = False
        col1,col2 = st.columns(2)
        with col1:
            image1 = st.file_uploader("Upload KTP Image", type=self.valid_image_extensions, key="image_1_key")
            if image1 is not None:
                image_full_path = self.base_ktp_image_local_path+image1.name
                is_image_1_ktp = self.is_image_ktp(image_full_path)
                if not is_image_1_ktp:
                    self.gui.show_error(self.invalid_ktp_msg)
                    invalid_ktp = True
                else: self.gui.show_success("KTP Is Valid!")

        if not self.checkbox:
            with col2: image2 = st.camera_input("Take A Picture")
        else:
            with col2: image2 = st.file_uploader("Upload Image To Verify", type=self.valid_image_extensions, key="image_2_key")

        return image1,image2,invalid_ktp

    def run_demo(self):
        image_1_path = "../images/image_for_face_verification/image_1_to_compare/"
        image_2_path = "../images/image_for_face_verification/image_2_to_compare/"
        image_1_list = os.listdir(image_1_path)
        image_2_list = os.listdir(image_2_path)
        for idx,(img1,img2) in enumerate(zip(image_1_list,image_2_list)):
            st.header(f"Case {idx+1}")
            self.verify_face(image_1_path+img1,image_2_path+img2,True,False)
            st.divider()