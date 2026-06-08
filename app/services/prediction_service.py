# app/services/prediction_service.py
import io
import os
import asyncio
from PIL import Image
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tensorflow.keras.models import load_model  # type: ignore
from huggingface_hub import hf_hub_download
from app.core.config import settings

from tensorflow.keras.applications.convnext import (  # type: ignore
    preprocess_input as convnext_preprocess,
)
from tensorflow.keras.applications.inception_v3 import (  # type: ignore
    preprocess_input as inception_preprocess,
)
from tensorflow.keras.applications.efficientnet import (  # type: ignore
    preprocess_input as efficientnet_preprocess,
)


class MultiModelPredictor:
    def __init__(self):
        self.age_model = None
        self.age_regression_model = None
        self.gender_model = None
        self.haircolor_model = None
        self.hairstyle_model = None
        self.eyebrows_model = None
        self.skin_model = None
        self.beard_model = None
        self.is_loaded = False

    def load_models(self):
        """ฟังก์ชันสำหรับโหลดโมเดลเก็บไว้ใน Class (ทำหน้าที่เป็น In-memory Cache)"""
        if self.is_loaded:
            return

        REPO_ID = "Jetsada117/models_project"
        print(f"Downloading and loading models from Hugging Face Hub: {REPO_ID}")

        def get_model(filename):
            path = hf_hub_download(
                repo_id=REPO_ID, filename=filename, token=settings.HF
            )
            return load_model(path)

        self.age_model = get_model("age_finetuned_model_convnext.keras")
        self.age_regression_model = get_model(
            "age_convnext_finetuned_regression_model.keras"
        )
        self.gender_model = get_model("gender_best_model_efficientnet.keras")
        self.haircolor_model = get_model("haircolor_best_model_convnext.keras")
        self.hairstyle_model = get_model("hairstyle_best_model_inception.keras")
        self.eyebrows_model = get_model("eyebrows_best_model_convnext.keras")
        self.skin_model = get_model("skin_best_model_inception.keras")
        self.beard_model = get_model("beard_best_model_convnext.keras")

        self.is_loaded = True
        print("All models loaded successfully!")

    def get_preprocessed_images(self, image_bytes: bytes):
        """
        เปิดรูปภาพและ resize ไว้ล่วงหน้าเพียงครั้งเดียวสำหรับขนาดที่ต้องใช้ (224 และ 299)
        เพื่อลดภาระของ CPU ในการประมวลผลซ้ำซ้อน
        """
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # เตรียมรูปขนาด 224 (สำหรับ ConvNeXt, EfficientNet)
        img_224 = np.array(img.resize((224, 224)), dtype=np.float32)
        img_224 = np.expand_dims(img_224, axis=0)
        
        # เตรียมรูปขนาด 299 (สำหรับ Inception)
        img_299 = np.array(img.resize((299, 299)), dtype=np.float32)
        img_299 = np.expand_dims(img_299, axis=0)

        return {
            "convnext": convnext_preprocess(img_224.copy()),
            "inception": inception_preprocess(img_299.copy()),
            "efficientnet": efficientnet_preprocess(img_224.copy()),
            "default": img_224 / 255.0
        }

    def _map_age_to_range(self, age: float) -> list:
        """
        แปลงอายุที่เป็นตัวเลข (float) เป็น One-hot encoding ตามช่วงวัยที่ต้องการ
        ตัวอย่าง: [0-18, 19-35, 36-50, 50+]
        """
        if age <= 6:
            return [1, 0, 0, 0, 0, 0]
        elif age <= 12:
            return [0, 1, 0, 0, 0, 0]
        elif age <= 25:
            return [0, 0, 1, 0, 0, 0]
        elif age <= 40:
            return [0, 0, 0, 1, 0, 0]
        elif age <= 65:
            return [0, 0, 0, 0, 1, 0]
        else:
            return [0, 0, 0, 0, 0, 1]

    def _predict_age_regression(self, processed_image):
        pred_age = self.age_regression_model.predict(processed_image, verbose=0)[0][0]
        return self._map_age_to_range(pred_age)

    def _predict_age(self, processed_image):
        pred_probs = self.age_model.predict(processed_image, verbose=0)[0]
        predicted_index = np.argmax(pred_probs)
        result = [0] * len(pred_probs)
        result[predicted_index] = 1
        return result

    def _predict_gender(self, processed_image):
        pred_prob = self.gender_model.predict(processed_image, verbose=0)[0][0]
        return [0, 1] if pred_prob > 0.5 else [1, 0]

    def _predict_haircolor(self, processed_image):
        pred_probs = self.haircolor_model.predict(processed_image, verbose=0)[0]
        predicted_index = np.argmax(pred_probs)
        result = [0] * len(pred_probs)
        result[predicted_index] = 1
        return result

    def _predict_hairstyle(self, processed_image):
        pred_probs = self.hairstyle_model.predict(processed_image, verbose=0)[0]
        predicted_index = np.argmax(pred_probs)
        if predicted_index == 0:
            return [0, 0]
        elif predicted_index == 1:
            return [1, 0]
        else:
            return [0, 1]

    def _predict_eyebrows(self, processed_image):
        pred_probs = self.eyebrows_model.predict(processed_image, verbose=0)[0]
        return [1 if prob > 0.5 else 0 for prob in pred_probs]

    def _predict_skin(self, processed_image):
        pred_probs = self.skin_model.predict(processed_image, verbose=0)[0]
        predicted_index = np.argmax(pred_probs)
        result = [0] * len(pred_probs)
        result[predicted_index] = 1
        return result

    def _predict_beard(self, processed_image):
        pred_probs = self.beard_model.predict(processed_image, verbose=0)[0]
        return [1 if prob > 0.5 else 0 for prob in pred_probs]

    async def predict_all(self, image_bytes: bytes) -> list:
        """รันโมเดลทั้งหมดพร้อมกันโดยใช้รูปที่ผ่านการ Preprocess ล่วงหน้าเพียงครั้งเดียว"""
        loop = asyncio.get_running_loop()
        
        # ทำ Preprocess เพียงครั้งเดียว (CPU intensive)
        preprocessed = await loop.run_in_executor(None, self.get_preprocessed_images, image_bytes)

        with ThreadPoolExecutor() as pool:

            async def get_hair_features():
                hairstyle_res = await loop.run_in_executor(
                    pool, self._predict_hairstyle, preprocessed["inception"]
                )

                if hairstyle_res == [0, 0]:
                    num_haircolor_classes = self.haircolor_model.output_shape[-1]
                    haircolor_res = [0] * num_haircolor_classes
                else:
                    haircolor_res = await loop.run_in_executor(
                        pool, self._predict_haircolor, preprocessed["convnext"]
                    )

                return haircolor_res, hairstyle_res

            task_age = loop.run_in_executor(
                pool, self._predict_age_regression, preprocessed["convnext"]
            )
            task_gender = loop.run_in_executor(pool, self._predict_gender, preprocessed["efficientnet"])
            task_hair = get_hair_features()
            task_eyebrows = loop.run_in_executor(
                pool, self._predict_eyebrows, preprocessed["convnext"]
            )
            task_skin = loop.run_in_executor(pool, self._predict_skin, preprocessed["inception"])
            task_beard = loop.run_in_executor(pool, self._predict_beard, preprocessed["convnext"])

            res_age, res_gender, res_hair, res_eyebrows, res_skin, res_beard = (
                await asyncio.gather(
                    task_age,
                    task_gender,
                    task_hair,
                    task_eyebrows,
                    task_skin,
                    task_beard,
                )
            )

        haircolor_res, hairstyle_res = res_hair

        predictions_dict = {
            "age_result": res_age,
            "gender_result": res_gender,
            "haircolor_result": haircolor_res,
            "hairstyle_result": hairstyle_res,
            "eyebrows_result": res_eyebrows,
            "skin_result": res_skin,
            "beard_result": res_beard,
        }

        return predictions_dict


predictor_service = MultiModelPredictor()
