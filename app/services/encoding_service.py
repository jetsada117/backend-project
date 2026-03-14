import numpy as np
import pandas as pd


class FeatureEncoder:
    def __init__(self):
        self.age_categories = [
            "วัยเด็กเล็ก",
            "วัยเด็กโต",
            "วัยรุ่น",
            "วัยผู้ใหญ่ตอนต้น",
            "วัยผู้ใหญ่ตอนกลาง",
            "วัยสูงอายุ",
        ]
        self.gender_categories = [
            "หญิง",
            "ชาย",
        ]
        self.hair_color_categories = [
            "ผมน้ำตาล",
            "ผมบลอนด์",
            "ผมดำ",
        ]
        self.hair_style_categories = ["ผมตรง", "ผมหยักศก"]
        self.eyebrow_categories = [
            "คิ้วโก่ง",
            "คิ้วหนา",
            "คิ้วตรง",
            "คิ้วบาง",
        ]
        self.skin_categories = [
            "ผิวขาว",
            "ผิวขาวเหลือง",
            "ผิวสองสี",
            "ผิวคล้ำ",
        ]
        self.beard_categories = [
            "เคราบาง",
            "หนวด",
            "เคราแพะ",
            "จอน",
        ]

        # รวมชื่อ Feature ทั้งหมดตามลำดับ
        self.feature_names = (
            self.age_categories
            + self.gender_categories
            + self.hair_color_categories
            + self.hair_style_categories
            + self.eyebrow_categories
            + self.skin_categories
            + self.beard_categories
        )

        self.age_mapping = {
            "เด็กเล็ก": "วัยเด็กเล็ก",
            "เด็กโต": "วัยเด็กโต",
            "วัยรุ่น": "วัยรุ่น",
            "ผู้ใหญ่ตอนต้น": "วัยผู้ใหญ่ตอนต้น",
            "ผู้ใหญ่ตอนกลาง": "วัยผู้ใหญ่ตอนกลาง",
            "สูงอายุ": "วัยสูงอายุ",
        }

    def _encode_one_hot(self, target_value, category_list):
        return [1 if target_value == category else 0 for category in category_list]

    def _encode_multi_hot(self, target_list, category_list):
        return [1 if category in target_list else 0 for category in category_list]

    def parse_text(self, text):
        """ฟังก์ชันสกัดข้อมูลจากข้อความให้อยู่ในรูปแบบ Dictionary"""
        text = text.replace(" ", "")
        extracted_features = {
            "age": None,
            "gender": None,
            "hair_color": None,
            "hair_style": None,
            "eyebrow": [],
            "skin": None,
            "beard": [],
        }

        for category in self.gender_categories:
            if category in text:
                extracted_features["gender"] = category

        for category in self.hair_color_categories:
            if category in text or category.replace("ผม", "") in text:
                extracted_features["hair_color"] = category

        for category in self.hair_style_categories:
            if category in text or category.replace("ผม", "") in text:
                extracted_features["hair_style"] = category

        for category in self.eyebrow_categories:
            if category in text:
                extracted_features["eyebrow"] = category

        for category in sorted(self.skin_categories, key=len, reverse=True):
            if category in text:
                extracted_features["skin"] = category
                break

        for key, value in self.age_mapping.items():
            if key in text:
                extracted_features["age"] = value

        # ดักหมวด Multi-label
        if "หนวดเคราบาง" in text:
            extracted_features["beard"].append("หนวดเคราบาง")
        elif "หนวดเข้ม" in text or "หนวด" in text:
            extracted_features["beard"].append("หนวดเข้ม")
        if "เคราแพะ" in text:
            extracted_features["beard"].append("เคราแพะ")
        if "จอน" in text:
            extracted_features["beard"].append("จอน")

        return extracted_features

    def text_to_vector(self, text, verbose=False):
        """ฟังก์ชันแปลงข้อความให้เป็น Vector"""
        parsed_data = self.parse_text(text)

        if verbose:
            print(f"ตีความได้ว่า: {parsed_data}")

        encoded_vector = []
        encoded_vector.extend(
            self._encode_one_hot(parsed_data["age"], self.age_categories)
        )
        encoded_vector.extend(
            self._encode_one_hot(parsed_data["gender"], self.gender_categories)
        )
        encoded_vector.extend(
            self._encode_one_hot(parsed_data["hair_color"], self.hair_color_categories)
        )
        encoded_vector.extend(
            self._encode_one_hot(parsed_data["hair_style"], self.hair_style_categories)
        )
        encoded_vector.extend(
            self._encode_multi_hot(parsed_data["eyebrow"], self.eyebrow_categories)
        )
        encoded_vector.extend(
            self._encode_one_hot(parsed_data["skin"], self.skin_categories)
        )
        encoded_vector.extend(
            self._encode_multi_hot(parsed_data["beard"], self.beard_categories)
        )

        return np.array(encoded_vector)

    def vector_to_text(self, vector):
        """
        ฟังก์ชันแปลง Vector [0, 1, 0, ...] กลับเป็นคำภาษาไทย
        โดยอิงจาก index ของ self.feature_names
        """
        matched_features = []
        for i, val in enumerate(vector):
            if val == 1:
                matched_features.append(self.feature_names[i])

        hair_style_start_idx = (
            len(self.age_categories)
            + len(self.gender_categories)
            + len(self.hair_color_categories)
        )
        hair_style_end_idx = hair_style_start_idx + len(self.hair_style_categories)

        hair_style_vector = vector[hair_style_start_idx:hair_style_end_idx]
        if sum(hair_style_vector) == 0:
            matched_features.append("ศีรษะล้าน")

        beard_start_idx = len(self.feature_names) - len(self.beard_categories)
        beard_vector = vector[beard_start_idx:]
        if sum(beard_vector) == 0:
            matched_features.append("ไม่มีหนวดเครา")

        return matched_features

    def to_dataframe(self, vector):
        """Helper Method สำหรับแสดงผลในรูปแบบ DataFrame แนวตั้ง"""
        df = pd.DataFrame([vector], columns=self.feature_names)
        return df.T


encoder = FeatureEncoder()
