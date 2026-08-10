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
        self.hair_style_categories = ["ผมตรง", "ผมหยักศก", "ศีรษะล้าน"]
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
            # วัยเด็กเล็ก (2-6 ปี)
            "เด็กเล็ก": "วัยเด็กเล็ก",
            "เด็กน้อย": "วัยเด็กเล็ก",
            "ทารก": "วัยเด็กเล็ก",
            "อนุบาล": "วัยเด็กเล็ก",
            
            # วัยเด็กโต (7-12 ปี)
            "เด็กโต": "วัยเด็กโต",
            "ประถม": "วัยเด็กโต",
            "เด็กประถม": "วัยเด็กโต",
            
            # วัยรุ่น (13-25 ปี)
            "วัยรุ่น": "วัยรุ่น",
            "มัธยม": "วัยรุ่น",
            "เด็กมัธยม": "วัยรุ่น",
            "มหาลัย": "วัยรุ่น",
            "มหาวิทยาลัย": "วัยรุ่น",
            "วัยเรียน": "วัยรุ่น",
            
            # วัยผู้ใหญ่ตอนต้น (26-40 ปี)
            "ผู้ใหญ่ตอนต้น": "วัยผู้ใหญ่ตอนต้น",
            "วัยทำงาน": "วัยผู้ใหญ่ตอนต้น",
            "คนวัยทำงาน": "วัยผู้ใหญ่ตอนต้น",
            
            # วัยผู้ใหญ่ตอนกลาง (41-65 ปี)
            "ผู้ใหญ่ตอนกลาง": "วัยผู้ใหญ่ตอนกลาง",
            "วัยกลางคน": "วัยผู้ใหญ่ตอนกลาง",
            "คนวัยกลางคน": "วัยผู้ใหญ่ตอนกลาง",
            
            # วัยสูงอายุ (66 ปีขึ้นไป)
            "สูงอายุ": "วัยสูงอายุ",
            "ผู้สูงอายุ": "วัยสูงอายุ",
            "คนแก่": "วัยสูงอายุ",
            "คนชรา": "วัยสูงอายุ",
            "วัยชรา": "วัยสูงอายุ",
            "ผู้เฒ่า": "วัยสูงอายุ"
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

        if "ศีรษะล้าน" in text:
            extracted_features["hair_style"] = "ศีรษะล้าน"

        for category in self.eyebrow_categories:
            if category in text:
                extracted_features["eyebrow"].append(category)

        for category in sorted(self.skin_categories, key=len, reverse=True):
            if category in text:
                extracted_features["skin"] = category
                break

        for key, value in self.age_mapping.items():
            if key in text:
                extracted_features["age"] = value

        if "เคราบาง" in text:
            extracted_features["beard"].append("เคราบาง")
        elif "หนวด" in text:
            extracted_features["beard"].append("หนวด")
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

        if sum(hair_style_vector) == 0 and "ศีรษะล้าน" not in matched_features:
            matched_features.append("ศีรษะล้าน")

        return matched_features

    def to_dataframe(self, vector):
        """Helper Method สำหรับแสดงผลในรูปแบบ DataFrame แนวตั้ง"""
        df = pd.DataFrame([vector], columns=self.feature_names)
        return df.T

    def combine_results_to_vector(self, pred_dict: dict) -> list:
        """รวมผลจากโมเดลทุกตัวเป็น Vector เดียว"""
        keys = [
            "age_result",
            "gender_result",
            "haircolor_result",
            "hairstyle_result",
            "eyebrows_result",
            "skin_result",
            "beard_result",
        ]
        full_vector = []
        for key in keys:
            full_vector.extend(pred_dict.get(key) or [])
        return full_vector

    def get_thai_description_dict(self, pred_dict: dict) -> dict:
        """แปลงผลจากโมเดล (Array) เป็นข้อความภาษาไทยสำหรับแต่ละฟีเจอร์"""
        try:
            age_text = self.age_categories[np.argmax(pred_dict["age_result"])]
            gender_text = self.gender_categories[np.argmax(pred_dict["gender_result"])]

            if sum(pred_dict["hairstyle_result"]) == 0:
                hairstyle_text = "ศีรษะล้าน"
                haircolor_text = ""
            else:
                hairstyle_text = self.hair_style_categories[
                    np.argmax(pred_dict["hairstyle_result"])
                ]
                haircolor_text = ""
                if sum(pred_dict["haircolor_result"]) > 0:
                    haircolor_text = self.hair_color_categories[
                        np.argmax(pred_dict["haircolor_result"])
                    ]

                if hairstyle_text == "ศีรษะล้าน":
                    haircolor_text = ""

            skin_text = self.skin_categories[np.argmax(pred_dict["skin_result"])]

            eyebrow_texts = [
                cat
                for i, cat in enumerate(self.eyebrow_categories)
                if pred_dict["eyebrows_result"][i] == 1
            ]
            eyebrow_string = ", ".join(eyebrow_texts)

            beard_texts = [
                cat
                for i, cat in enumerate(self.beard_categories)
                if pred_dict["beard_result"][i] == 1
            ]
            beard_string = ", ".join(beard_texts)

            return {
                "age": age_text,
                "gender": gender_text,
                "haircolor": haircolor_text,
                "hairstyle": hairstyle_text,
                "eyebrows": eyebrow_string,
                "skin": skin_text,
                "beard": beard_string,
            }
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"ข้อมูลผลลัพธ์ไม่ถูกต้อง: {str(e)}")


encoder = FeatureEncoder()
