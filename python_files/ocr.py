import cv2
import json
import re
import pytesseract
import streamlit as st
import os
import pandas as pd
import numpy as np
from test_file import Test
from jaro import jaro_winkler_metric
from cachetools import cached, TTLCache
from program_timer import timeit
from math import ceil

cache = TTLCache(maxsize=1, ttl=14400)

class KTPInformation:
    def __init__(self):
        self.Provinsi = None
        self.KotaAtauKabupaten = None
        self.NIK = None
        self.Nama = None
        self.TempatLahir = None
        self.TanggalLahir = None
        self.JenisKelamin = None
        self.GolonganDarah = "-"
        self.Alamat = None
        self.RT = None
        self.RW = None
        self.KelurahanAtauDesa = None
        self.Kecamatan = None
        self.Agama = None
        self.StatusPerkawinan = None
        self.Pekerjaan = None
        self.Kewarganegaraan = None
        self.BerlakuHingga = None

    def reset_values(self):
        self.Provinsi = None
        self.KotaAtauKabupaten = None
        self.NIK = None
        self.Nama = None
        self.TempatLahir = None
        self.TanggalLahir = None
        self.JenisKelamin = None
        self.GolonganDarah = "-"
        self.Alamat = None
        self.RT = None
        self.RW = None
        self.KelurahanAtauDesa = None
        self.Kecamatan = None
        self.Agama = None
        self.StatusPerkawinan = None
        self.Pekerjaan = None
        self.Kewarganegaraan = None
        self.BerlakuHingga = None

class Verifier:
    def __init__(self, dataframe: pd.DataFrame):
        self.unique_pronvisi_column = dataframe["Provinsi"].unique()
        self.unique_kota_kabupaten_column = dataframe["DaerahTingkatDua"].unique()
        self.unique_kecamatan_column = dataframe["Kecamatan"].unique()
        self.verifier_dict = {}
        self.jakarta_pattern = [
            "JAKARTA BARAT","JAKARTA PUSAT","JAKARTA TIMUR","JAKARTA SELATAN","JAKARTA UTARA",
            'Jakarta Barat', 'Jakarta Pusat', 'Jakarta Timur', 'Jakarta Selatan', 'Jakarta Utara'
            ]
        self.goldar_pattern = r"AB[-+]?|A[-+]?|B[-+]?|O[-+]?"
        self.agama_pattern = [
            "ISLAM","KRISTEN","KATOLIK","BUDHA","HINDU","KONGHUCHU","CHRISTIAN",
            ]
        self.gender_pattern = "LAKI-LAKI|PEREMPUAN|MALE|FEMALE|LAKILAKI|LAKI|Laki-Laki|Perempuan|Male|Female|LakiLaki|Laki"
        self.status_perkawinan_pattern = "BELUM KAWIN|KAWIN|CERAI HIDUP|CERAI MATI|MARRIED|Belum Kawin|Kawin|Cerai Hidup|Cerai Mati|Married"

    @cached(cache)
    def make_verifier_dict(self):
        self.verifier_dict["provinsi"] = self.unique_pronvisi_column
        self.verifier_dict["kota_kabupaten"] = self.unique_kota_kabupaten_column
        self.verifier_dict["jakarta"] = self.jakarta_pattern
        self.verifier_dict["goldar"] = self.goldar_pattern
        self.verifier_dict["agama"] = self.agama_pattern
        self.verifier_dict["gender"] = self.gender_pattern
        self.verifier_dict["jobs"] = ['BELUM/TIDAK BEKERJA', 'MENGURUS RUMAH TANGGA', 'PELAJAR/MAHASISWA', 'PENSIUNAN', 'PEWAGAI NEGERI SIPIL', 'TENTARA NASIONAL INDONESIA', 'KEPOLISISAN RI', 'PERDAGANGAN', 'PETANI/PEKEBUN', 'PETERNAK', 'NELAYAN/PERIKANAN', 'INDUSTRI', 'KONSTRUKSI', 'TRANSPORTASI', 'KARYAWAN SWASTA', 'KARYAWAN BUMN', 'KARYAWAN BUMD', 'KARYAWAN HONORER', 'BURUH HARIAN LEPAS', 'BURUH TANI/PERKEBUNAN', 'BURUH NELAYAN/PERIKANAN', 'BURUH PETERNAKAN', 'PEMBANTU RUMAH TANGGA', 'TUKANG CUKUR', 'TUKANG LISTRIK', 'TUKANG BATU', 'TUKANG KAYU', 'TUKANG SOL SEPATU', 'TUKANG LAS/PANDAI BESI', 'TUKANG JAHIT', 'TUKANG GIGI', 'PENATA RIAS', 'PENATA BUSANA', 'PENATA RAMBUT', 'MEKANIK', 'SENIMAN', 'TABIB', 'PARAJI', 'PERANCANG BUSANA', 'PENTERJEMAH', 'IMAM MASJID', 'PENDETA', 'PASTOR', 'WARTAWAN', 'USTADZ/MUBALIGH', 'JURU MASAK', 'PROMOTOR ACARA', 'ANGGOTA DPR-RI', 'ANGGOTA DPD', 'ANGGOTA BPK', 'PRESIDEN', 'WAKIL PRESIDEN', 'ANGGOTA MAHKAMAH KONSTITUSI', 'ANGGOTA KABINET/KEMENTERIAN', 'DUTA BESAR', 'GUBERNUR', 'WAKIL GUBERNUR', 'BUPATI', 'WAKIL BUPATI', 'WALIKOTA', 'WAKIL WALIKOTA', 'ANGGOTA DPRD PROVINSI', 'ANGGOTA DPRD KABUPATEN/KOTA', 'DOSEN', 'GURU', 'PILOT', 'PENGACARA', 'NOTARIS', 'ARSITEK', 'AKUNTAN', 'KONSULTAN', 'DOKTER', 'BIDAN', 'PERAWAT', 'APOTEKER', 'PSIKIATER/PSIKOLOG', 'PENYIAR TELEVISI', 'PENYIAR RADIO', 'PELAUT', 'PENELITI', 'SOPIR', 'PIALANG', 'PARANORMAL', 'PEDAGANG', 'PERANGKAT DESA', 'KEPALA DESA', 'BIARAWATI', 'WIRASWASTA','PEKERJAAN LAINNYA','PEGAWAI SWASTA','OTHERS','PEGAWAI NEGERI SIPIL (PNS)']
        self.verifier_dict["status_perkawinan"] = self.status_perkawinan_pattern
        self.verifier_dict["kecamatan"] = self.unique_kecamatan_column
        return self.verifier_dict

class KTPOCR:
    def __init__(self, is_demo: bool):
        self.page_title = "KTP OCR Demo"
        self.page_icon = "../images/other_images/icon_image.png"
        self.set_page_title_and_icon(is_demo)
        if is_demo:
            st.title(self.page_title)
            self.checkbox = st.checkbox("Show All KTP",value=True)
        self.hide_side_menu = False
        self.hide_footer = True
        self.hide_styles(self.hide_side_menu,self.hide_footer)
        # Change this to your pytesseract installation path
        self.pytesseract_path = r"C:\Users\chris\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
        self.base_path = "../ktp_classification/ktp_images/valid_ktp/"
        self.file_path = None
        self.image = None
        self.original_image = None
        self.gray = None
        self.result = KTPInformation()
        self.image_name = None
        self.image_name_for_test = None
        self.tester = None
        self.choice = None
        self.verified = None
        self.threshold_num = None
        self.ocr_threshold = st.slider(label='OCR Threshold', min_value=0.5, max_value=1.0, step=0.05, value=0.8)
        self.data_kode_wilayah_df = pd.read_excel("../data/data_kode_wilayah.xlsx")
        self.verifier = None
        self.verifier_maker = None
        self.jaro_winkler_threshold = 0.8
        self.tricky_case_threshold = 0.9
        self.preprocessed = False
        self.special_characters = ['!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~']
        self.regex_patterns = {
            "date": r'(\d{2})[/-]?(\d{2})[/-]?\s?(\d{4})',
            "nik" : r'\d+\s*',
            "tempat_tanggal_lahir": r'(?:[A-Z][A-Za-z.-]+\s)?(?:\d{2}-\d{2}(?:\s\d{4})?|\d{2}\d{2}(?:\s\d{2,4})?)',
        }
        self.total_ktp_information = 18

    def set_page_title_and_icon(self, is_demo: bool):
        if is_demo: st.set_page_config(page_title=self.page_title,page_icon=self.page_icon,layout="wide")

    def process(self):
        pytesseract.pytesseract.tesseract_cmd = self.pytesseract_path
        if self.image_name in ["ktp_vina.png","ktp_amat.jpg","ktp_lilly.png"]: threshed_value = 187
        elif self.image_name == "ktp_abdurrauf.png": threshed_value = 127
        elif self.image_name == "ktp_supriadi.png": threshed_value = 210
        elif self.image_name == "ktp_luki.png": threshed_value = 87
        elif self.image_name == "ktp_gilang.jpg": threshed_value = 150
        elif self.image_name == "ktp_debby.jpg": threshed_value = 210
        elif self.image_name == "ktp_jelty.png": threshed_value = 89
        elif self.image_name == "ktp_galang.png": threshed_value = 70
        elif self.image_name == "ktp_sulistyono.png": threshed_value = 140
        elif self.image_name == "ktp_muhammad.png": threshed_value = 132
        # elif self.image_name == "ktp_ren.jpg": threshed_value = 140
        elif self.image_name == "ktp_sarip.png": threshed_value = 89
        elif self.image_name == "ktp_yasir.jpeg": threshed_value = 140
        elif self.image_name == "ktp_yopi.png": threshed_value = 140
        else: threshed_value = self.otsu_threshold(self.gray)
        # threshed_value = self.otsu_threshold(self.gray)
        th, threshed = cv2.threshold(self.gray, threshed_value, 255, cv2.THRESH_TRUNC)
        raw_extracted_text = pytesseract.image_to_string((threshed), lang="ind")
        return self.clean_special_characters_text(raw_extracted_text), threshed,threshed_value

    def otsu_threshold(self, image: str):
        bins_num = 256
        hist, bin_edges = np.histogram(image, bins=bins_num)
        bin_mids = (bin_edges[:-1] + bin_edges[1:]) / 2.
        weight1 = np.cumsum(hist)
        weight2 = np.cumsum(hist[::-1])[::-1]
        mean1 = np.cumsum(hist * bin_mids) / weight1
        mean2 = (np.cumsum((hist * bin_mids)[::-1]) / weight2[::-1])[::-1]
        inter_class_variance = weight1[:-1] * weight2[1:] * (mean1[:-1] - mean2[1:]) ** 2
        index_of_max_val = np.argmax(inter_class_variance)
        threshold = ceil(bin_mids[:-1][index_of_max_val])
        return threshold

    def get_ktp_image_name(self, is_test: bool):
        full_file_name = os.path.split(self.file_path)[-1]
        if is_test: return full_file_name.split('_')[1].split('.')[0]
        else: return full_file_name

    def clean_special_characters_text(self, raw_text: str):
        things_to_clean = {
            "--": "",
            "—": "",
            "“": "",
            "~": "",
            "'": "",
            "+": "",
            "[": "",
            "\\": "",
            "@": "",
            "^": "",
            "{": "",
            "%": "",
            "(": "",
            '"': "",
            "*": "",
            "|": "",
            ",": "",
            "&": "",
            "<": "",
            "`": "",
            "}": "",
            "_": "",
            "=": "",
            "]": "",
            "!": "",
            ">": "",
            ";": "",
            "#": "",
            "$": "",
            ")": "",
        }

        return self.replace_letter_from_word_dict(raw_text, things_to_clean)

    def clean_semicolons_and_stripes(self, text: str):
        things_to_clean = {
            ":": "",
            "-": "",
        }

        return self.replace_letter_from_word_dict(text, things_to_clean)

    def remove_semicolons(self, text: str):
        text = text.replace(":","")
        return text

    def remove_dots(self, text: str):
        text = text.replace(".","")
        return text

    def replace_letter_from_word_dict(self, text: str, replacements: dict): return ''.join(replacements.get(letter, letter) for letter in text)

    def word_to_number_converter(self, word):
        word_dict = {
            '|' : "1"
        }
        return self.replace_letter_from_word_dict(word, word_dict)

    def extract(self, extracted_result:str):
        lines = self.compact(extracted_result.split("\n"))
        gender_pattern = self.verifier_maker["gender"].split("|")
        status_perkawinan_pattern = self.verifier_maker["status_perkawinan"].split("|")
        dates_list = [item for item in lines if re.search(self.regex_patterns['date'], item) and self.is_valid_date(self.add_dash_to_date(item))]

        # EDGE CASES VARIABLES
        edge_cases = {
            "tempat_lahir": False,
            "job": False,
            "kewarganegaraan": False,
            "agama": False,
            "rt_rw": False,
            "kecamatan": False,
            "kelurahan_desa": False,
            "alamat": False,
            "jenis_kelamin": False,
            "status_perkawinan": False,
            "berlaku_hingga": False,
            "tanggal_lahir": False,
        }

        # NORMAL CASES VARIABLES
        normal_cases = {
            "name": False,
            "nik": False,
        }

        for idx,word in enumerate(lines):
            info = word.split(" ")[0].strip()
            if info in self.special_characters:
                try: info = word.split(" ")[1].strip()
                except: pass

            if not normal_cases['nik']:
                match = re.search(self.regex_patterns["nik"], word)
                if match:
                    if self.find_string_similarity(word, "NIK") >= self.jaro_winkler_threshold: self.extract_nik(word, True)
                    else: self.extract_nik(word, False)
                    normal_cases['nik'] = True

            #* EXTRACT PROVINSI
            if self.find_string_similarity(info,"PROVINSI") >= self.jaro_winkler_threshold: self.extract_provinsi(word)

            #* EXTRACT KOTA KABUPATEN NON JAKARTA
            if any(self.find_string_similarity(info, keyword) >= self.jaro_winkler_threshold for keyword in ["KOTA", "KABUPATEN"]): self.extract_kota_kabupaten(word, False)

            #* EXTRACT KOTA KABUPATEN JAKARTA
            if self.find_string_similarity(info,"JAKARTA") >= self.jaro_winkler_threshold: self.extract_kota_kabupaten(word,True)

            #* EXTRACT NAMA
            if not normal_cases['name'] and self.find_string_similarity(info,"Nama") >= self.jaro_winkler_threshold:
                extra_name = lines[idx+1]
                self.extract_name(word, extra_name)
                normal_cases['name'] = True

            #* EXTRACT TEMPAT TANGGAL LAHIR
            if self.find_string_similarity(info,"TempatTgl") >= self.jaro_winkler_threshold: self.extract_tempat_tanggal_lahir(word)

            #* EXTRACT GOLONGAN DARAH AND JENIS
            if self.find_string_similarity(info,"Jenis") >= self.jaro_winkler_threshold: self.extract_golongan_darah_and_jenis_kelamin(word)

            #* EXTRACT GOLONGAN DARAH EDGE CASES
            try:
                if re.search(self.verifier_maker['gender'], info)[0]: self.extract_golongan_darah_and_jenis_kelamin(word)
            except: pass

            #* EXTRACT ALAMAT
            if self.find_string_similarity(info,"Alamat") >= self.jaro_winkler_threshold:
                extra_alamat = lines[idx+1]
                if self.find_string_similarity(extra_alamat.split(" ")[0], "Status") < self.jaro_winkler_threshold: self.extract_alamat(word, extra_alamat)

            #* EXTRACT KECAMATAN
            if self.find_string_similarity(info,"Kecamatan") >= self.jaro_winkler_threshold: self.extract_kecamatan(word)

            #* EXTRACT KELURAHAN ATAU DESA
            if self.find_string_similarity(info,"Kel/Desa") >= self.jaro_winkler_threshold: self.extract_kelurahan_atau_desa(word)

            #* EXTRACT KEWARGANEGARAAN
            if self.find_string_similarity(info,"Kewarganegaraan") >= self.jaro_winkler_threshold: self.extract_kewarganegaraan(word)

            #* EXTRACT PEKERJAAN
            if self.find_string_similarity(info,"Pekerjaan") >= self.jaro_winkler_threshold: self.extract_pekerjaan(word)

            #* EXTRACT AGAMA
            if self.find_string_similarity(info,"Agama") >= self.jaro_winkler_threshold: self.extract_agama(word)

            #* EXTRACT STATUS PERKAWINAN
            if self.find_string_similarity(info,"Status") >= self.jaro_winkler_threshold: self.extract_perkawinan(word)

            #* EXTRACT RT/RW
            if self.find_string_similarity(info,"RT/RW") >= self.jaro_winkler_threshold: self.extract_rt_rw(word)

            #* EXTRACT BERLAKU HINGGA SEUMUR HIDUP
            if self.find_string_similarity(info,"SEUMUR") >= self.jaro_winkler_threshold: self.result.BerlakuHingga = "SEUMUR HIDUP"

            #* EXTRACT BERLAKU HINGGA
            if self.find_string_similarity(info,"Berlaku") >= self.jaro_winkler_threshold: self.extract_berlaku_hingga(word)

        #* HANDLE EDGE CASES
        if any(value is None or (isinstance(value, str) and value.strip() == "") for value in self.result.__dict__.values()) or (isinstance(self.result.Kewarganegaraan, str) and len(self.result.Kewarganegaraan) < 3) or (isinstance(self.result.Kecamatan, str) and len(self.result.Kecamatan) < 3) or (isinstance(self.result.KelurahanAtauDesa, str) and len(self.result.KelurahanAtauDesa) < 3) or (isinstance(self.result.StatusPerkawinan, str) and len(self.result.StatusPerkawinan) < 5) or (isinstance(self.result.BerlakuHingga, str) and len(self.result.BerlakuHingga) < 5):
            for info in lines:
                info = info.lstrip(":").lstrip()
                #* HANDLE PEKERJAAN EDGE CASES
                if not edge_cases['job'] and (self.result.Pekerjaan is None or self.result.Pekerjaan.strip() == ""):
                    try:
                        pekerjaan = self.clean_semicolons_and_stripes(info)
                        split_pekerjaan = pekerjaan.split(" ")
                        check_kota_kabupaten = " ".join(split_pekerjaan[1:]).strip()
                        if self.find_string_similarity(self.result.KotaAtauKabupaten,check_kota_kabupaten) >= self.jaro_winkler_threshold: pekerjaan = split_pekerjaan[0].strip()

                        best_match, best_similarity = self.find_best_match_from_verifier_pattern(self.verifier_maker["jobs"], pekerjaan)
                        if best_match and best_similarity >= self.tricky_case_threshold:
                            self.result.Pekerjaan = best_match.strip()
                            edge_cases['job'] = True
                    except: pass

                #* HANDLE TEMPAT LAHIR AND TANGGAL LAHIR EDGE CASES
                if not edge_cases['tempat_lahir'] and (self.result.TempatLahir is None or self.result.TempatLahir.strip() == "" or self.find_string_similarity(self.result.TempatLahir,"TempatTgl") >= self.jaro_winkler_threshold or self.result.TanggalLahir is None or self.result.TanggalLahir.strip() == "" or self.find_string_similarity(self.result.TanggalLahir,"Lahir") >= self.jaro_winkler_threshold):
                    try:
                        matches = re.search(self.regex_patterns["tempat_tanggal_lahir"], info.strip())[0]
                        if matches:
                            tempat_lahir, tanggal_lahir = matches.split(" ")
                            tempat_lahir = self.remove_dots(tempat_lahir)
                            if (self.result.TempatLahir is None or self.result.TempatLahir.strip() == ""): self.result.TempatLahir = tempat_lahir.strip()
                            if ((self.result.TanggalLahir is None or self.result.TanggalLahir.strip() == "" or self.find_string_similarity(self.result.TanggalLahir,"Lahir") >= self.jaro_winkler_threshold) and len(tanggal_lahir) > 8):
                                self.result.TanggalLahir = tanggal_lahir.strip()
                            edge_cases['tempat_lahir'] = True
                    except: pass

                #* HANDLE TANGGAL LAHIR EDGE CASES
                if not edge_cases['tanggal_lahir'] and (self.result.TanggalLahir is None or self.result.TanggalLahir.strip() == "" or self.find_string_similarity(self.result.TanggalLahir,"Lahir") >= self.jaro_winkler_threshold):
                    try:
                        matches = re.search(self.regex_patterns["date"], info.strip())[0]
                        if self.find_string_similarity(matches,self.result.NIK) < 0.75:
                            self.result.TanggalLahir = matches.strip()
                            edge_cases['tanggal_lahir'] = True
                    except: pass

                #* HANDLE KEWARGANEGARAAN EDGE CASES
                if not edge_cases['kewarganegaraan'] and ((isinstance(self.result.Kewarganegaraan, str) and len(self.result.Kewarganegaraan) < 3) or self.result.Kewarganegaraan is None or self.result.Kewarganegaraan.strip() == ""):
                    self.result.Kewarganegaraan = "WNI"
                    edge_cases['kewarganegaraan'] = True

                #* HANDLE AGAMA EDGE CASES
                if not edge_cases['agama'] and (self.result.Agama is None or self.result.Agama.strip() == ""):
                    best_match, best_similarity = self.find_best_match_from_verifier_pattern(self.verifier_maker["agama"], info)
                    if best_match and best_similarity >= self.tricky_case_threshold:
                        self.result.Agama = best_match.strip()
                        self.handle_agama_katholik()
                        edge_cases['agama'] = True

                #* HANDLE RT/RW EDGE CASES
                if not edge_cases['rt_rw'] and (self.result.RT is None or self.result.RT.strip() == "" or self.result.RW is None or self.result.RW.strip() == ""):
                    if self.find_string_similarity(info,"-/-") >= self.jaro_winkler_threshold:
                        if '/' in info: info = info.split('/')
                        rt,rw = info[0],info[-1]
                        self.result.RT = rt.strip()
                        self.result.RW = rw.strip()
                        edge_cases['rt_rw'] = True
                    if info.count('0') >= 2 and len(info) < 12:
                        if "/" in info: info = info.split('/')
                        try:
                            rt = info[0].strip()
                            rw = info[1].strip()
                            if len(rt) < 3 or len(rw) < 3: rt,rw = self.process_rt_rw(info)
                            rt = self.clean_semicolons_and_stripes(rt)
                            self.result.RT = rt
                            self.result.RW = rw
                            edge_cases['rt_rw'] = True
                        except:
                            self.result.RT = None
                            self.result.RW = None


                #* HANDLE KELURAHAN ATAU DESA EDGE CASES
                if not edge_cases['kelurahan_desa'] and (self.result.KelurahanAtauDesa is None or self.result.KelurahanAtauDesa.strip() == "" or (isinstance(self.result.KelurahanAtauDesa, str) and len(self.result.KelurahanAtauDesa) < 3)):
                    try:
                        best_match, best_similarity = self.find_best_match_from_verifier_pattern(self.verifier_maker["kota_kabupaten"], info.strip())
                        if best_match and best_similarity >= self.tricky_case_threshold:
                            self.result.KelurahanAtauDesa = best_match.strip()
                            edge_cases['kelurahan_desa'] = True
                    except: pass

                #* HANDLE KECAMATAN EDGE CASES
                if not edge_cases['kecamatan'] and (self.result.Kecamatan is None or self.result.Kecamatan.strip() == "" or (isinstance(self.result.Kecamatan, str) and len(self.result.Kecamatan) < 3)):
                    try:
                        best_match, best_similarity = self.find_best_match_from_verifier_pattern(self.verifier_maker["kecamatan"], info)
                        if best_match and best_similarity >= self.tricky_case_threshold:
                            self.result.Kecamatan = best_match.strip()
                            edge_cases['kecamatan'] = True
                    except: pass

                #* HANDLE ALAMAT EDGE CASES
                if not edge_cases['alamat'] and (self.result.Alamat is None or self.result.Alamat.strip() == "" or (isinstance(self.result.Alamat, str) and len(self.result.Alamat) < 7)):

                    if any(substring in info for substring in ["BLOK", "JL","1L","NO","IL","IX","DUSUN"]):
                        alamat = self.clean_semicolons_and_stripes(info)
                        self.result.Alamat = alamat.lstrip(".").strip()
                        edge_cases['alamat'] = True

                #* HANDLE JENIS KELAMIN EDGE CASES
                if not edge_cases['jenis_kelamin'] and (self.result.JenisKelamin is None or self.result.JenisKelamin.strip() == ""):
                    try:
                        gender = info.split(" ")[0].strip()
                        best_match, best_similarity = self.find_best_match_from_verifier_pattern(gender_pattern, gender)
                        if best_match and best_similarity >= self.tricky_case_threshold:
                            self.result.JenisKelamin = best_match.strip()
                            self.handle_gender_laki()
                            edge_cases['jenis_kelamin'] = True
                    except: pass

                #* HANDLE STATUS PERKAWINAN EDGE CASES
                if not edge_cases['status_perkawinan'] and (self.result.StatusPerkawinan is None or self.result.StatusPerkawinan.strip() == "" or (isinstance(self.result.StatusPerkawinan, str) and len(self.result.StatusPerkawinan) < 5)):
                    try:
                        best_match, best_similarity = self.find_best_match_from_verifier_pattern(status_perkawinan_pattern, info.strip())
                        if best_match and best_similarity >= self.tricky_case_threshold:
                            self.result.StatusPerkawinan = best_match.strip()
                            edge_cases['status_perkawinan'] = True
                    except: pass

                #* HANDLE BERLAKU HINGGA EDGE CASES
                if not edge_cases['berlaku_hingga'] and (self.result.BerlakuHingga is None or self.result.BerlakuHingga.strip() == "" or (isinstance(self.result.BerlakuHingga, str) and len(self.result.BerlakuHingga) < 5)):
                    try:
                        berlaku_hingga = dates_list[1]
                        berlaku_hingga = self.remove_all_letters(berlaku_hingga, True)
                        self.result.BerlakuHingga = berlaku_hingga.strip()
                        edge_cases['berlaku_hingga'] = True
                    except: pass

        #* HANDLE NAME EDGE CASES
        if self.result.NIK is not None and (self.result.Nama is None or self.result.Nama.strip() == ""):
            for idx,word in enumerate(lines):
                try:
                    if self.find_string_similarity(self.result.NIK, word) >= self.jaro_winkler_threshold:
                        name = lines[idx+1]
                        name = self.clean_name(name)
                        self.result.Nama = name.strip()
                        break
                except: pass

        #* HANDLE NAME EDGE CASES 2
        if self.result.Nama is not None and self.find_string_similarity("Nama",self.result.Nama) >= self.jaro_winkler_threshold:
            for idx,word in enumerate(lines):
                try:
                    if self.find_string_similarity(self.result.KotaAtauKabupaten, word) >= self.jaro_winkler_threshold:
                        name = lines[idx+1]
                        name = self.clean_name(name)
                        self.result.Nama = name.strip()
                        break
                except: pass

    def compact(self, lst: list): return list(filter(None, lst))

    def handle_agama_katholik(self):
        if self.find_string_similarity(self.result.Agama, "KATHOLIK") >= self.jaro_winkler_threshold: self.result.Agama = "KATHOLIK"

    def handle_gender_laki(self):
        if self.find_string_similarity(self.result.JenisKelamin, "LAKI") >= self.jaro_winkler_threshold: self.result.JenisKelamin = "LAKI-LAKI"

    def is_valid_date(self, date_str: str):
        try:
            day, month, year = map(int, date_str.split('-'))
            if 1 <= day <= 31 and 1 <= month <= 12 and year > 0:
                if (month in [4, 6, 9, 11] and day <= 30) or (month != 2 and day <= 31): return True
                elif month == 2:
                    if (year % 400 == 0) or (year % 4 == 0 and year % 100 != 0): return day <= 29
                    else: return day <= 28
        except: pass
        return False

    def remove_all_letters(self, text: str, is_date: bool):
        if is_date: text = re.sub('[^\d-]', '', text)
        else: text = re.sub(r"[^\d]", "", text)
        return text

    def add_dash_to_date(self, date_str):
        match = re.search(self.regex_patterns["date"], date_str)
        if match:
            day, month, year = match.groups()
            return f"{day}-{month}-{year}"
        return date_str

    def extract_nik(self, word, is_nik_in_word):
        missed_extracted_letters = {
            'b': "6",
            'e': "2",
            '?': '7',
        }

        if is_nik_in_word: word = word.split(":")[-1].replace(" ", "")

        word = self.replace_letter_from_word_dict(word, missed_extracted_letters)
        word = self.remove_all_letters(word, is_date=False)
        self.result.NIK = word.strip()

    def extract_alamat(self, word: str, extra_alamat: str):
        try:
            alamat_typo = word.split(" ")[0].strip()
            if self.find_string_similarity(alamat_typo,"Alamat") >= self.jaro_winkler_threshold: alamat = self.word_to_number_converter(word).replace(alamat_typo, "")
        except: pass
        try:
            alamat_parts = alamat.split("Agama", 1)
            alamat = alamat_parts[0]
            alamat = self.clean_semicolons_and_stripes(alamat).strip()
            if self.result.Alamat: self.result.Alamat += alamat.lstrip(".").strip()
            else: self.result.Alamat = alamat.lstrip(".").strip()
            if self.find_string_similarity(extra_alamat.split(" ")[0].strip(), "RT/RW") < self.jaro_winkler_threshold:
                alamat = self.result.Alamat + " "+extra_alamat
                self.result.Alamat = alamat.lstrip(".").strip()
        except: self.result.Alamat = None

    def extract_berlaku_hingga(self, word):
        if ':' in word: word = word.split(":")
        elif "-" in word: word = word.split("-")
        try:
            berlaku_hingga = word[1]
            if len(berlaku_hingga) <= 3:
                word = word.replace("Berlaku Hingga","")
                berlaku_hingga = word
            if self.find_string_similarity(berlaku_hingga,"SEUMUR HIDUP") >= 0.7: self.result.BerlakuHingga = "SEUMUR HIDUP"
            else:
                berlaku_hingga = self.remove_all_letters(berlaku_hingga, True)
                berlaku_hingga = self.add_dash_to_date(berlaku_hingga)
                self.result.BerlakuHingga = berlaku_hingga.strip()
        except: self.result.BerlakuHingga = None

    def extract_kewarganegaraan(self, word):
        try:
            if ":" in word: word = word.split(":")
            kewarganegaraan = word[1]
            kewarganegaraan = self.clean_semicolons_and_stripes(kewarganegaraan)
            kewarganegaraan = self.remove_dots(kewarganegaraan)
            check_kewarganegaraan = kewarganegaraan.split(" ")

            if len(check_kewarganegaraan) > 1: kewarganegaraan = check_kewarganegaraan[0]
            self.result.Kewarganegaraan = kewarganegaraan.strip()

        except: self.result.Kewarganegaraan = None

    def extract_kecamatan(self, word):
        try:
            if ":" in word: word = word.split(":")
            elif "." in word: word = word.split(".")
            elif "-" in word: word = word.split("-")
            else: word = word.split(" ")
            # st.success(word)
            kecamatan = word[1]
            # st.success(kecamatan)
            self.result.Kecamatan = kecamatan.strip()
        except: self.result.Kecamatan = None

    def extract_perkawinan(self,word):
        try:
            status_perkawinan = re.search(self.verifier_maker["status_perkawinan"],word)[0]
            # st.success(status_perkawinan)
            self.result.StatusPerkawinan = status_perkawinan.strip()
        except:self.result.StatusPerkawinan = None

    def clean_kelurahan_atau_desa(self, kelurahan_atau_desa: str):
        kelurahan_atau_desa = self.clean_semicolons_and_stripes(kelurahan_atau_desa)
        kelurahan_atau_desa = self.remove_dots(kelurahan_atau_desa)
        kelurahan_atau_desa = self.remove_all_digits(kelurahan_atau_desa)
        return kelurahan_atau_desa

    def extract_kelurahan_atau_desa(self, word):
        if ":" in word: word = word.split(':')
        elif "-" in word: word = word.split('-')
        else: word = word.split()
        try:
            kelurahan_atau_desa = "".join(word[1:]).strip()
            kelurahan_atau_desa = self.clean_kelurahan_atau_desa(kelurahan_atau_desa)
            self.result.KelurahanAtauDesa = kelurahan_atau_desa
        except: self.result.KelurahanAtauDesa = kelurahan_atau_desa

    def extract_pekerjaan(self, word):
        try:
            word = word.split()
            pekerjaan = []
            for wr in word: pekerjaan.append(wr)
            pekerjaan = ' '.join(pekerjaan).replace(word[0], '').strip()
            pekerjaan = self.clean_semicolons_and_stripes(pekerjaan)
            check_pekerjaan = pekerjaan.split(" ")
            pekerjaan_suffix = " ".join(check_pekerjaan[1:])
            if self.find_string_similarity(pekerjaan_suffix,self.result.KotaAtauKabupaten) >= self.jaro_winkler_threshold: pekerjaan = check_pekerjaan[0]
            best_match, best_similarity = self.find_best_match_from_verifier_pattern(self.verifier_maker["jobs"], pekerjaan)
            if best_match and best_similarity >= self.jaro_winkler_threshold: self.result.Pekerjaan = best_match.strip()
        except: self.result.Pekerjaan = None

    def process_rt_rw(self, digits: str):
        if len(digits) == 6:
            rt = digits[:len(digits)//2]
            rw = digits[len(digits)//2:]
        else:
            matches = re.findall(r'0(\w{2})', digits)
            rt = "0"+matches[0]
            rw = "0"+matches[1]

        return rt.strip(),rw.strip()

    def extract_rt_rw(self, word):
        rtrw = word.split(" ")[0].strip()
        try:
            if self.find_string_similarity(rtrw, "RT/RW") >= self.jaro_winkler_threshold:
                pattern = re.compile(re.escape(rtrw))
                word = pattern.sub(" ", word).strip()
                digits = self.remove_all_letters(word, False)

                if digits: rt,rw = self.process_rt_rw(digits)

                else:
                    rt = None
                    rw = None

                rt = self.remove_dots(rt)
                rw = self.remove_dots(rw)
                self.result.RT = rt
                self.result.RW = rw
            else:
                self.result.RT = None
                self.result.RW = None
        except:
            self.result.RT = None
            self.result.RW = None

    def extract_golongan_darah_and_jenis_kelamin(self, word):
        try:
            if word[0] == ":": word = word.replace(":", " ")
            gender_match = re.search(self.verifier_maker['gender'], word)
            if gender_match:
                self.result.JenisKelamin = gender_match.group()
                self.handle_gender_laki()
            if ":" in word: word = word.split(':')
            else: word = word.split(" ")
            word = self.compact(word)
            if word[-1].islower(): word.pop()
            goldar = word[-1].strip()
            if goldar == "Q" or goldar == "6" or goldar == "0": goldar = "O"
            goldar_match = re.search(self.verifier_maker['goldar'], goldar)
            if goldar_match: self.result.GolonganDarah = goldar_match.group().strip()
        except: self.result.GolonganDarah = "-"

    def extract_agama(self, word):
        try:
            word = word.replace("Agama","")
            agama = self.clean_semicolons_and_stripes(word).strip()
            best_match, best_similarity = self.find_best_match_from_verifier_pattern(self.verifier_maker["agama"], agama)
            if best_match and best_similarity >= self.jaro_winkler_threshold:
                self.result.Agama = best_match.strip()
                self.handle_agama_katholik()
        except: self.result.Agama = None

    def find_best_match_from_verifier_pattern(self, pattern_list: list, word: str):
        best_match = None
        best_similarity = 0
        for pattern in pattern_list:
            similarity = self.find_string_similarity(pattern, word)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = pattern
        return best_match, best_similarity

    def extract_provinsi(self, word):
        try:
            word = word.split(" ")
            if len(word) == 1: provinsi = word[0].replace("PROVINSI", " ").strip()
            else:
                provinsi = " ".join(word[1:])
                provinsi = self.clean_semicolons_and_stripes(provinsi)

            pattern_list = self.verifier_maker["provinsi"]
            best_match, best_similarity = self.find_best_match_from_verifier_pattern(pattern_list, provinsi)

            if best_match and best_similarity >= self.jaro_winkler_threshold: self.result.Provinsi = ("PROVINSI "+best_match).strip()
            else: self.result.Provinsi = None
        except: self.result.Provinsi = None

    def extract_kota_kabupaten(self, word, is_jakarta: bool):
        if is_jakarta:
            pattern_list = self.verifier_maker["jakarta"]
            try:
                best_match, best_similarity = self.find_best_match_from_verifier_pattern(pattern_list, word)
                if best_match and best_similarity >= self.jaro_winkler_threshold: self.result.KotaAtauKabupaten = best_match.strip()
            except: self.result.KotaAtauKabupaten = None
        else:
            pattern_list = self.verifier_maker["kota_kabupaten"]
            word = word.split(" ")
            if "KOTA" in word: index = word.index("KOTA")
            elif "KABUPATEN" in word: index = word.index("KABUPATEN")

            try: word = word[index:]
            except: pass

            kota_kabupaten = " ".join(word[1:])
            try:
                best_match, best_similarity = self.find_best_match_from_verifier_pattern(pattern_list, kota_kabupaten)
                if best_match and best_similarity >= self.jaro_winkler_threshold: self.result.KotaAtauKabupaten = word[0] + " "+best_match.strip()
            except: self.result.KotaAtauKabupaten = None

    def remove_all_digits(self, text: str): return re.sub(r'\d', '', text)

    def clean_name(self, name: str):
        name = self.clean_semicolons_and_stripes(name)
        name = self.remove_all_digits(name)
        name = self.remove_dots(name)
        return name

    def extract_name(self, word, extra_name: str):
        try:
            word = word.split(" ")
            if ':' in word: word.remove(":")
            word = self.compact(word)
            if self.find_string_similarity(word[0].strip(),"Nama") >= self.jaro_winkler_threshold: word.remove(word[0])
            name = " ".join(word)
            if self.find_string_similarity(extra_name, "Tempat/TglLahir") < 0.6: name += " "+extra_name
            name = self.clean_name(name)
            self.result.Nama = name.strip()
        except: self.result.Nama = None

    def has_no_digits(strings_list): return not any(char.isdigit() for string in strings_list for char in string)

    def isalpha_withspaces(self, input_str):
        for char in input_str:
            if char != ' ' and not char.isalpha():
                return False
        return True

    def extract_tempat_tanggal_lahir(self, word):
        try:
            word = word.split(" ")
            word = self.compact(word)
            if len(word[-1]) < 3: word.pop()
            word = [i for i in word if self.find_string_similarity(i, "TempatTgl") < self.jaro_winkler_threshold and self.find_string_similarity(i, "Lahir") < self.jaro_winkler_threshold]
            if ':' in word: word.remove(':')
            tempat_lahir, tanggal_lahir = " ".join(word[:-1]),word[-1]
            tempat_lahir = self.remove_dots(tempat_lahir)
            if not self.isalpha_withspaces(tempat_lahir) or len(tempat_lahir) < 3:
                for i in range (len(word)-1,-1,-1):
                    if word[i].isalpha():
                        tempat_lahir = word[i]
                        tanggal_lahir = "-".join(word[i+1:])
                        break
            tempat_lahir = self.clean_semicolons_and_stripes(tempat_lahir)
            tempat_lahir = self.remove_dots(tempat_lahir)
            tempat_lahir = self.remove_all_digits(tempat_lahir)
            try: tanggal_lahir = self.remove_all_letters(tanggal_lahir)
            except: pass
            self.result.TanggalLahir = tanggal_lahir.strip()
            self.result.TempatLahir = tempat_lahir.strip()

        except: self.result.TempatLahir = None

    def master_process(self):
        raw_text,threshed,threshed_value = self.process()
        self.extract(raw_text)
        return threshed,threshed_value

    def to_json(self): return json.dumps(self.result.__dict__, indent=4)

    def json_to_pandas_dataframe(self, json_file: json):
        df = pd.DataFrame.from_dict(json_file, orient="index")
        df.columns = ["Value"]
        df.rename_axis("Information",inplace=True)
        return df

    def get_test_df(self): return self.tester.run()

    def make_dataframe(self):
        json_object = json.loads(self.to_json())
        df = self.json_to_pandas_dataframe(json_object)
        test_column = self.get_test_df()
        df['Should Return'] = test_column
        df['Value'] = df['Value'].astype(str)
        df['Should Return'] = df['Should Return'].astype(str)
        df['Check'] = np.where(df.apply(lambda row: self.find_string_similarity(row['Value'], row['Should Return']) >= self.jaro_winkler_threshold, axis=1), '✅', '❌')
        df['Similarity'] = df.apply(lambda row: f"{self.find_string_similarity(row['Value'], row['Should Return']) * 100:.0f}%", axis=1)
        return df, json_object

    def verify_ocr(self, df: pd.DataFrame):
        threshold = int(self.ocr_threshold*self.total_ktp_information)
        check_counts = df['Check'].value_counts()
        num_correct = check_counts.get('✅', 0)
        if num_correct >= threshold: return True,num_correct,threshold
        else: return False,num_correct,threshold

    def get_all_files(self): return os.listdir(self.base_path)

    def showSelectBox(self):
        all_files = self.get_all_files()
        choice = st.selectbox("Select KTP File", all_files)
        return choice

    def preprocess_data_kode_wilayah_df(self):
        if self.preprocessed: return
        self.data_kode_wilayah_df = self.data_kode_wilayah_df.loc[:, ~self.data_kode_wilayah_df.columns.str.contains('^Unnamed')]
        self.data_kode_wilayah_df['Provinsi'] = self.data_kode_wilayah_df['Provinsi'].apply(lambda x: x.upper())
        self.data_kode_wilayah_df['Kecamatan'] = self.data_kode_wilayah_df['Kecamatan'].apply(lambda x: x.upper())
        self.data_kode_wilayah_df['DaerahTingkatDua'] = self.data_kode_wilayah_df['DaerahTingkatDua'].apply(lambda x: x.upper())
        self.data_kode_wilayah_df['DaerahTingkatDua'] = self.data_kode_wilayah_df['DaerahTingkatDua'].apply(lambda x: " ".join(x.split()[1:]))
        self.data_kode_wilayah_df["Provinsi"] = self.data_kode_wilayah_df["Provinsi"].replace({
            'ACEH (NAD)': 'ACEH',
            'NUSA TENGGARA TIMUR (NTT)': 'NUSA TENGGARA TIMUR',
            'NUSA TENGGARA BARAT (NTB)': 'NUSA TENGGARA BARAT',
            'DI YOGYAKARTA': 'DAERAH ISTIMEWA YOGYAKARTA'
        })
        self.add_kecamatan_to_df()
        self.preprocessed = True

    def add_kecamatan_to_df(self):
        additional_kecamatan = ["KEBAYORAN BARU","KALIWATES"]
        for kecamatan in additional_kecamatan: self.data_kode_wilayah_df['Kecamatan'] = pd.Series([kecamatan] + self.data_kode_wilayah_df['Kecamatan'].to_list())

    def hide_styles(self, hide_main_menu: bool, hide_footer: bool):
        style_string = ""

        if hide_main_menu:
            style_string += """
            #MainMenu {visibility: hidden}
            """

        if hide_footer:
            style_string += """
            footer {visibility: hidden}
            """

        if style_string:
            style_html = f"<style>{style_string}</style>"
            st.markdown(style_html, unsafe_allow_html=True)

    def find_string_similarity(self, string1: str, string2: str): return round(jaro_winkler_metric(string1,string2),2)

    def init(self, show_all_ktp: bool, image_path: str, is_kyc: bool):
        self.result.reset_values()
        if not is_kyc:
            if show_all_ktp: self.file_path = self.base_path + image_path
            else: self.file_path = self.base_path + self.choice
        else: self.file_path = self.base_path + image_path.name

        self.image = cv2.imread(self.file_path)
        self.original_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        self.gray = cv2.GaussianBlur(self.gray, (3, 3), 0)
        self.image_name = self.get_ktp_image_name(False)
        self.image_name_for_test = self.get_ktp_image_name(True)
        self.tester = Test(self.image_name_for_test)

    def display_results(self):
        self.preprocess_data_kode_wilayah_df()
        self.verifier = Verifier(self.data_kode_wilayah_df)
        self.verifier_maker = self.verifier.make_verifier_dict()
        threshed,threshed_value = self.master_process()
        st.header(f'{self.image_name} - Threshed Value: {threshed_value}')

        col1, col2 = st.columns(2)
        with col2:
            aspect_ratio = self.original_image.shape[1] / self.original_image.shape[0]
            new_width = int(335 * aspect_ratio)
            resized_original_image = cv2.resize(self.original_image, (new_width, 250))
            resized_threshed_image = cv2.resize(threshed, (new_width, 250))
            st.image(resized_original_image, use_column_width=True)
            st.image(resized_threshed_image, use_column_width=True)

        df, extracted_ktp_record = self.make_dataframe()
        self.verified,num_correct,self.threshold_num = self.verify_ocr(df)

        with col1: st.dataframe(df,use_container_width=True,height=670)

        show_ratio = f"{num_correct}/{self.total_ktp_information}"
        show_threshold = f" Threshold: {self.threshold_num}"

        col4,col5,col6 = st.columns(3)
        with col4: st.info(show_ratio+show_threshold)
        with col5:
            if self.verified: st.success("VERIFIED!")
            else: st.error("NOT VERIFIED!")
        with col6:
            df['percentage_match'] = pd.to_numeric(df['Similarity'].str.rstrip('%'))
            average_percentage = df['percentage_match'].mean()
            st.info(f"Average Percentage Match: {average_percentage:.2f}%")

        return df, extracted_ktp_record

    def show_all_ktp_demo(self, is_kyc: bool):
        all_ktp_files = self.get_all_files()
        for data in all_ktp_files:
            self.init(True, data,is_kyc)
            self.display_results()

    def show_individual_ktp(self, is_kyc: bool):
        self.choice = self.showSelectBox()
        if self.choice: self.init(False,"",is_kyc)
        self.display_results()

    def run_demo(self, is_kyc: bool):
        if self.checkbox: self.show_all_ktp_demo(is_kyc)
        else: self.show_individual_ktp(is_kyc)

    def run(self,ktp_image,is_kyc):
        self.init(False, ktp_image,is_kyc)
        df, extracted_ktp_record = self.display_results()
        return df, extracted_ktp_record