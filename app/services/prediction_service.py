# app/services/prediction_service.py
import os
import io
import logging
import warnings
import asyncio
import numpy as np
from PIL import Image
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tensorflow.keras.models import load_model

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

warnings.filterwarnings("ignore", category=UserWarning, module="keras")
warnings.filterwarnings("ignore", category=DeprecationWarning)

logging.getLogger("tensorflow").setLevel(logging.ERROR)


class MultiModelPredictor:
    def __init__(self):
        current_file_path = Path(__file__).resolve()

        app_dir = current_file_path.parent.parent

        model_path = os.path.join(app_dir, "machine_models")

        print(f"Loading model from: {model_path}")

        self.age_model = load_model(
            os.path.join(model_path, "age_finetuned_model_convnext.keras")
        )
        self.gender_model = load_model(
            os.path.join(model_path, "gender_efficientnet_base_model.keras")
        )
        self.haircolor_model = load_model(
            os.path.join(model_path, "haircolor_inceptionv3_finetuned_best_model.keras")
        )
        self.hairstyle_model = load_model(
            os.path.join(model_path, "hair_bald_inceptionv3_finetuned_best_model.keras")
        )
        self.eyebrows_model = load_model(
            os.path.join(model_path, "eyebrows_convnext_finetuned_model.keras")
        )
        self.skin_model = load_model(
            os.path.join(model_path, "skin_inception_finetuned_model.keras")
        )
        self.beard_model = load_model(
            os.path.join(
                model_path, "beard_weight_classification_finetuned_convnext_model.keras"
            )
        )

    def preprocess_image(self, image_bytes: bytes, img_size: int, rescale: bool = True):
        """
        ฟังก์ชันสำหรับเตรียมรูปภาพก่อนเข้าโมเดล
        """
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        img = img.resize((img_size, img_size))

        img_array = np.array(img, dtype=np.float32)

        if rescale:
            img_array = img_array / 255.0

        img_array = np.expand_dims(img_array, axis=0)
        return img_array

    def _predict_age(self, image_bytes: bytes):
        processed_image = self.preprocess_image(image_bytes, img_size=224)
        pred_probs = self.age_model.predict(processed_image)[0]

        predicted_index = np.argmax(pred_probs)
        result = [0] * len(pred_probs)
        result[predicted_index] = 1
        return result

    def _predict_gender(self, image_bytes: bytes):
        processed_image = self.preprocess_image(
            image_bytes, img_size=224, rescale=False
        )
        pred_prob = self.gender_model.predict(processed_image)[0][0]

        return [0, 1] if pred_prob > 0.5 else [1, 0]

    def _predict_haircolor(self, image_bytes: bytes):
        processed_image = self.preprocess_image(image_bytes, img_size=299)
        pred_probs = self.haircolor_model.predict(processed_image)[0]

        predicted_index = np.argmax(pred_probs)
        result = [0] * len(pred_probs)
        result[predicted_index] = 1
        return result

    def _predict_hairstyle(self, image_bytes: bytes):
        processed_image = self.preprocess_image(image_bytes, img_size=299)
        pred_probs = self.hairstyle_model.predict(processed_image)[0]

        predicted_index = np.argmax(pred_probs)

        if predicted_index == 0:
            return [0, 0]
        elif predicted_index == 1:
            return [1, 0]
        else:
            return [0, 1]

    def _predict_eyebrows(self, image_bytes: bytes):
        processed_image = self.preprocess_image(image_bytes, img_size=224)
        pred_probs = self.eyebrows_model.predict(processed_image)[0]

        return [1 if prob > 0.5 else 0 for prob in pred_probs]

    def _predict_skin(self, image_bytes: bytes):
        processed_image = self.preprocess_image(image_bytes, img_size=299)
        pred_probs = self.skin_model.predict(processed_image)[0]

        predicted_index = np.argmax(pred_probs)
        result = [0] * len(pred_probs)
        result[predicted_index] = 1
        return result

    def _predict_beard(self, image_bytes: bytes):
        processed_image = self.preprocess_image(image_bytes, img_size=224)
        pred_probs = self.beard_model.predict(processed_image)[0]

        # คืนค่าเป็น List ของ 0 และ 1 (เช่น [1, 0, 1, 0])
        return [1 if prob > 0.5 else 0 for prob in pred_probs]

    async def predict_all(self, image_bytes: bytes) -> list:
        """รันโมเดลทั้งหมดพร้อมกันด้วย ThreadPool โดยมีเงื่อนไขข้ามการทำนายสีผมหากศีรษะล้าน"""
        loop = asyncio.get_running_loop()

        with ThreadPoolExecutor() as pool:

            async def get_hair_features():
                hairstyle_res = await loop.run_in_executor(
                    pool, self._predict_hairstyle, image_bytes
                )

                if hairstyle_res == [0, 0]:
                    num_haircolor_classes = self.haircolor_model.output_shape[-1]
                    haircolor_res = [0] * num_haircolor_classes
                else:
                    haircolor_res = await loop.run_in_executor(
                        pool, self._predict_haircolor, image_bytes
                    )

                return haircolor_res, hairstyle_res

            task_age = loop.run_in_executor(pool, self._predict_age, image_bytes)
            task_gender = loop.run_in_executor(pool, self._predict_gender, image_bytes)
            task_hair = get_hair_features()
            task_eyebrows = loop.run_in_executor(
                pool, self._predict_eyebrows, image_bytes
            )
            task_skin = loop.run_in_executor(pool, self._predict_skin, image_bytes)
            task_beard = loop.run_in_executor(pool, self._predict_beard, image_bytes)

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
