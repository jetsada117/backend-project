import numpy as np


class FaceSimilarityScorer:
    def __init__(self, weight_config=None, group_sizes=None, multi_label_keys=None):
        """
        กำหนดค่าเริ่มต้นของน้ำหนักและขนาดของแต่ละกลุ่ม (Features)
        """
        self.weight_config = weight_config or {
            "age": 0.15,
            "gender": 0.40,
            "hair_color": 0.05,
            "hair_style": 0.05,
            "eyebrow": 0.10,
            "skin": 0.20,
            "beard": 0.05,
        }

        self.group_sizes = group_sizes or {
            "age": 6,
            "gender": 2,
            "hair_color": 3,
            "hair_style": 3,
            "eyebrow": 4,
            "skin": 4,
            "beard": 4,
        }

        self.multi_label_keys = multi_label_keys or ["eyebrow", "beard"]

        self.expanded_weights = self._build_expanded_weights()

    def _build_expanded_weights(self):
        """
        ฟังก์ชันภายใน (Private Method) สำหรับขยายค่าน้ำหนักตามจำนวนคลาส
        """
        ordered_keys = [
            "age",
            "gender",
            "hair_color",
            "hair_style",
            "eyebrow",
            "skin",
            "beard",
        ]

        expanded_weights = []
        for key in ordered_keys:
            w = self.weight_config[key]
            size = self.group_sizes[key]

            if key in self.multi_label_keys:
                w_per_dim = w / size
                expanded_weights.extend([w_per_dim] * size)
            else:
                expanded_weights.extend([w] * size)

        return np.array(expanded_weights)

    def calculate_similarity(self, vector_a: list, vector_b: list) -> float:
        """
        คำนวณค่าความคล้ายคลึงแบบ Dynamic Weighted Cosine Similarity
        """
        A = np.array(vector_a)
        B = np.array(vector_b)
        w = self.expanded_weights.copy()

        if len(A) != len(w) or len(B) != len(w):
            raise ValueError(
                f"ความยาวของ Vector ไม่ถูกต้อง (A={len(A)}, B={len(B)}, w={len(w)})"
            )

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
        คำนวณ Dynamic Weighted Cosine Similarity ระหว่าง 1 Vector กับ Matrix ของ DB พร้อมกันทั้งหมด
        vector_a: shape (26,)
        matrix_b: shape (N, 26)
        """
        w = self.expanded_weights

        if vector_a.shape[0] != len(w) or matrix_b.shape[1] != len(w):
            raise ValueError(
                f"ความยาวของ Vector ไม่ถูกต้อง (A={vector_a.shape[0]}, B={matrix_b.shape[1]}, w={len(w)})"
            )

        active_mask = vector_a != 0
        dynamic_w = w * active_mask

        if np.sum(dynamic_w) == 0:
            return np.zeros(matrix_b.shape[0])

        A_w = vector_a * dynamic_w
        numerator = np.dot(matrix_b, A_w)

        norm_a = np.sqrt(np.sum(dynamic_w * (vector_a**2)))
        norm_b = np.sqrt(np.sum((matrix_b**2) * dynamic_w, axis=1))

        denominator = norm_a * norm_b
        denominator[denominator == 0] = 1e-9

        return numerator / denominator


scorer = FaceSimilarityScorer()
