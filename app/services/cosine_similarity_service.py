import numpy as np


class FaceSimilarityScorer:
    def __init__(self, weight_config=None, group_sizes=None):
        """
        กำหนดค่าเริ่มต้นของน้ำหนักและขนาดของแต่ละกลุ่ม (Features)
        """

        self.weight_config = weight_config or {
            "age": 0.15,  # ช่วงวัย
            "gender": 0.40,  # เพศ
            "hair_color": 0.05,  # สีผม
            "hair_style": 0.05,  # ลักษณะผม
            "eyebrow": 0.10,  # คิ้ว
            "skin": 0.20,  # สีผิว
            "beard": 0.05,  # หนวดเครา
        }

        self.group_sizes = group_sizes or [
            6,  # Age (6 ช่วงวัย)
            2,  # Gender (ชาย, หญิง)
            3,  # Hair Color (ดำ, น้ำตาล, บลอนด์)
            3,  # Hair Style (ตรง, หยักศก, ศีรษะล้าน)
            4,  # Eyebrow (โก่ง, หนา, ตรง, บาง)
            4,  # Skin (ขาว, คล้ำ)
            4,  # Beard (4 แบบ)
        ]

        self.expanded_weights = self._build_expanded_weights()

    def _build_expanded_weights(self):
        """
        ฟังก์ชันสำหรับขยายค่าน้ำหนักตามจำนวนคลาส
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

    def calculate_similarity_matrix(
        self, vector_a: np.ndarray, matrix_b: np.ndarray
    ) -> np.ndarray:
        """
        คำนวณ Weighted Cosine Similarity ระหว่าง 1 Vector กับ Matrix ของ DB พร้อมกันทั้งหมด
        vector_a: shape (25,)
        matrix_b: shape (N, 25)
        """
        w = self.expanded_weights

        active_mask = vector_a != 0
        dynamic_w = w * active_mask

        if np.sum(dynamic_w) == 0:
            return np.zeros(matrix_b.shape[0])

        A_w = vector_a * dynamic_w
        B_w = matrix_b * dynamic_w

        numerator = np.dot(B_w, A_w)

        norm_a = np.sqrt(np.sum(A_w**2))
        norm_b = np.sqrt(np.sum(B_w**2, axis=1))

        denominator = norm_a * norm_b
        denominator[denominator == 0] = 1e-9

        return numerator / denominator


scorer = FaceSimilarityScorer()
