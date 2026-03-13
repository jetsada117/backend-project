import numpy as np


class FaceSimilarityScorer:
    def __init__(self, weight_config=None, group_sizes=None):
        """
        กำหนดค่าเริ่มต้นของน้ำหนักและขนาดของแต่ละกลุ่ม (Features)
        """
        # 1. กำหนดค่าน้ำหนัก Default (ถ้าไม่มีการส่งค่าใหม่เข้ามาตอนสร้าง Object)
        self.weight_config = weight_config or {
            "age": 0.15,  # ช่วงวัย
            "gender": 0.40,  # เพศ
            "hair_color": 0.5,  # สีผม
            "hair_style": 0.5,  # ลักษณะผม
            "eyebrow": 0.10,  # คิ้ว
            "skin": 0.20,  # สีผิว
            "beard": 0.5,  # หนวดเครา
        }

        # 2. กำหนดขนาดของคลาส (One-Hot length) ของแต่ละ Feature
        self.group_sizes = group_sizes or [
            6,  # Age (6 ช่วงวัย)
            2,  # Gender (ชาย, หญิง)
            3,  # Hair Color (ดำ, น้ำตาล, บลอนด์)
            2,  # Hair Style (ตรง, หยักศก)
            4,  # Eyebrow (โก่ง, หนา, ตรง, บาง)
            4,  # Skin (ขาว, คล้ำ)
            4,  # Beard (4 แบบ)
        ]

        self.expanded_weights = self._build_expanded_weights()

    def _build_expanded_weights(self):
        """
        ฟังก์ชันภายใน (Private Method) สำหรับขยายค่าน้ำหนักตามจำนวนคลาส
        """
        ordered_weights = [
            self.weight_config["age"],
            self.weight_config["gender"],
            self.weight_config["hair_color"],
            self.weight_config["hair_style"],
            self.weight_config["eyebrow"],
            self.weight_config["skin"],
            self.weight_config["beard"],
        ]

        expanded_weights = []
        for w, size in zip(ordered_weights, self.group_sizes):
            expanded_weights.extend([w] * size)

        return np.array(expanded_weights)

    def calculate_similarity(self, vector_a: list, vector_b: list) -> float:
        """
        คำนวณค่าความคล้ายคลึงแบบ Weighted Cosine Similarity
        """
        A = np.array(vector_a)
        B = np.array(vector_b)
        w = self.expanded_weights.copy()

        if len(A) != len(w) or len(B) != len(w):
            raise ValueError("ความยาวของ Vector ไม่ถูกต้อง")

        active_mask = A != 0
        dynamic_w = w * active_mask

        if np.sum(dynamic_w) == 0:
            return 0.0

        numerator = np.sum(dynamic_w * A * B)
        num_a = np.sqrt(np.sum(dynamic_w * (A**2)))
        num_b = np.sqrt(np.sum(dynamic_w * (B**2)))

        if num_a == 0 or num_b == 0:
            return 0.0

        similarity = numerator / (num_a * num_b)
        return float(similarity)


scorer = FaceSimilarityScorer()
