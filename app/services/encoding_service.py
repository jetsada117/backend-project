import numpy as np
import pandas as pd


class FeatureEncoder:
    def __init__(self):
        self.age_cats = [
            "วัยเด็กเล็ก",
            "วัยเด็กโต",
            "วัยรุ่น",
            "วัยผู้ใหญ่ตอนต้น",
            "วัยผู้ใหญ่ตอนกลาง",
            "วัยสูงอายุ",
        ]
        self.gender_cats = [
            "หญิง",
            "ชาย",
        ]
        self.hair_color_cats = [
            "ผมน้ำตาล",
            "ผมบลอนด์",
            "ผมดำ",
        ]
        self.hair_style_cats = ["ผมตรง", "ผมหยักศก"]
        self.eyebrow_cats = [
            "คิ้วโก่ง",
            "คิ้วหนา",
            "คิ้วตรง",
            "คิ้วบาง",
        ]
        self.skin_cats = [
            "ผิวขาว",
            "ผิวขาวเหลือง",
            "ผิวสองสี",
            "ผิวคล้ำ",
        ]
        self.beard_cats = [
            "หนวดเคราบาง",
            "หนวดเข้ม",
            "เคราแพะ",
            "จอน",
        ]

        self.all_columns = (
            self.age_cats
            + self.gender_cats
            + self.hair_color_cats
            + self.hair_style_cats
            + self.eyebrow_cats
            + self.skin_cats
            + self.beard_cats
        )

        self.age_mapping = {
            "เด็กเล็ก": "วัยเด็กเล็ก",
            "เด็กโต": "วัยเด็กโต",
            "วัยรุ่น": "วัยรุ่น",
            "วัยผู้ใหญ่ตอนต้น": "วัยผู้ใหญ่ตอนต้น",
            "วัยผู้ใหญ่ตอนกลาง": "วัยผู้ใหญ่ตอนกลาง",
            "สูงอายุ": "วัยสูงอายุ",
        }

    def _encode_one_hot(self, target_value, category_list):
        return [1 if target_value == cat else 0 for cat in category_list]

    def _encode_multi_hot(self, target_list, category_list):
        return [1 if cat in target_list else 0 for cat in category_list]

    def parse_text(self, text):
        """ฟังก์ชันแปลข้อความเป็น Dictionary"""
        text = text.replace(" ", "")
        data = {
            "age": None,
            "gender": None,
            "hair_color": None,
            "hair_style": None,
            "eyebrow": None,
            "skin": None,
            "beard": [],
        }

        for cat in self.gender_cats:
            if cat in text:
                data["gender"] = cat

        for cat in self.hair_color_cats:
            if cat in text or cat.replace("ผม", "") in text:
                data["hair_color"] = cat

        for cat in self.hair_style_cats:
            if cat in text or cat.replace("ผม", "") in text:
                data["hair_style"] = cat

        for cat in self.eyebrow_cats:
            if cat in text:
                data["eyebrow"] = cat

        for cat in sorted(self.skin_cats, key=len, reverse=True):
            if cat in text:
                data["skin"] = cat
                break

        for key, value in self.age_mapping.items():
            if key in text:
                data["age"] = value

        # ดักหมวด Multi-label
        if "หนวดเคราบาง" in text:
            data["beard"].append("หนวดเคราบาง")
        elif "หนวดเข้ม" in text or "หนวด" in text:
            data["beard"].append("หนวดเข้ม")
        if "เคราแพะ" in text:
            data["beard"].append("เคราแพะ")
        if "จอน" in text:
            data["beard"].append("จอน")

        return data

    def text_to_vector(self, text, verbose=False):
        """ฟังก์ชันแปลงข้อความให้เป็น Vector"""
        parsed_data = self.parse_text(text)

        if verbose:
            print(f"ตีความได้ว่า: {parsed_data}")

        full_vector = []
        full_vector.extend(self._encode_one_hot(parsed_data["age"], self.age_cats))
        full_vector.extend(
            self._encode_one_hot(parsed_data["gender"], self.gender_cats)
        )
        full_vector.extend(
            self._encode_one_hot(parsed_data["hair_color"], self.hair_color_cats)
        )
        full_vector.extend(
            self._encode_one_hot(parsed_data["hair_style"], self.hair_style_cats)
        )
        full_vector.extend(
            self._encode_multi_hot(parsed_data["eyebrow"], self.eyebrow_cats)
        )
        full_vector.extend(self._encode_one_hot(parsed_data["skin"], self.skin_cats))
        full_vector.extend(
            self._encode_multi_hot(parsed_data["beard"], self.beard_cats)
        )

        return np.array(full_vector)

    def to_dataframe(self, vector):
        """Helper Method สำหรับแสดงผลในรูปแบบ DataFrame แนวตั้ง"""
        df = pd.DataFrame([vector], columns=self.all_columns)
        return df.T


encoder = FeatureEncoder()
