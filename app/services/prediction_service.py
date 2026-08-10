# app/services/prediction_service.py
import io
import os
import asyncio
import threading
import numpy as np
import cv2
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tensorflow as tf  # type: ignore
from tensorflow import keras  # type: ignore
from tensorflow.keras import layers  # type: ignore
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


class RandomShear(layers.Layer):
    def __init__(self, shear_range=0.1, **kwargs):
        super(RandomShear, self).__init__(**kwargs)
        self.shear_range = shear_range

    def call(self, images, training=None):
        if not training:
            return images
        batch_size = tf.shape(images)[0]
        height = tf.shape(images)[1]
        width = tf.shape(images)[2]
        shear = tf.random.uniform([batch_size], -self.shear_range, self.shear_range)
        zeros = tf.zeros_like(shear)
        ones = tf.ones_like(shear)
        transforms = tf.stack(
            [ones, shear, zeros, zeros, ones, zeros, zeros, zeros], axis=1
        )
        return tf.raw_ops.ImageProjectiveTransformV2(
            images=images,
            transforms=transforms,
            output_shape=[height, width],
            interpolation="BILINEAR",
        )

    def get_config(self):
        config = super(RandomShear, self).get_config()
        config.update({"shear_range": self.shear_range})
        return config


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

        # สร้าง ThreadPoolExecutor เพียงครั้งเดียวเพื่อใช้ซ้ำ (Singleton Pattern)
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count() or 4)

        # Lock สำหรับโหลดโมเดลเพื่อป้องกัน Race Condition
        self._lock = threading.Lock()

        # Initialize OpenCV Face and Eye detectors
        self.face_cascade = cv2.CascadeClassifier(
            os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        )
        self.eye_cascade = cv2.CascadeClassifier(
            os.path.join(cv2.data.haarcascades, "haarcascade_eye.xml")
        )

    def _align_and_crop_face(self, image_np):
        """
        ทำ Face Alignment (หมุนให้ตาตรง) และ Crop เฉพาะใบหน้า โดยใช้ OpenCV Haar Cascades
        """
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) == 0:
            return image_np

        x, y, w, h = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
        roi_gray = gray[y : y + h, x : x + w]

        eyes = self.eye_cascade.detectMultiScale(roi_gray)

        if len(eyes) >= 2:
            eyes = sorted(eyes, key=lambda e: e[1])[:2]
            eyes = sorted(eyes, key=lambda e: e[0])

            ex1, ey1, ew1, eh1 = eyes[0]
            ex2, ey2, ew2, eh2 = eyes[1]

            eye_left = (x + ex1 + ew1 // 2, y + ey1 + eh1 // 2)
            eye_right = (x + ex2 + ew2 // 2, y + ey2 + eh2 // 2)

            dY = eye_right[1] - eye_left[1]
            dX = eye_right[0] - eye_left[0]
            angle = np.degrees(np.arctan2(dY, dX))

            eye_center = (
                float((eye_right[0] + eye_left[0]) / 2),
                float((eye_right[1] + eye_left[1]) / 2),
            )
            M = cv2.getRotationMatrix2D(eye_center, float(angle), 1.0)
            image_np = cv2.warpAffine(
                image_np,
                M,
                (image_np.shape[1], image_np.shape[0]),
                flags=cv2.INTER_CUBIC,
            )

            gray_rot = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            faces_rot = self.face_cascade.detectMultiScale(gray_rot, 1.3, 5)
            if len(faces_rot) > 0:
                x, y, w, h = sorted(faces_rot, key=lambda f: f[2] * f[3], reverse=True)[
                    0
                ]

        pad_w = int(w * 0.2)
        pad_h = int(h * 0.2)

        y1 = max(0, y - pad_h)
        y2 = min(image_np.shape[0], y + h + pad_h)
        x1 = max(0, x - pad_w)
        x2 = min(image_np.shape[1], x + w + pad_w)

        return image_np[y1:y2, x1:x2]

    def load_models(self):
        """ฟังก์ชันสำหรับโหลดโมเดลเก็บไว้ใน Class (ทำหน้าที่เป็น In-memory Cache)"""
        if self.is_loaded:
            return

        with self._lock:
            # Double-checked locking ป้องกันโหลดซ้ำซ้อนในสภาวะ concurrent
            if self.is_loaded:
                return

            REPO_ID = "Jetsada117/models_project"
            print(f"Downloading and loading models from Hugging Face Hub: {REPO_ID}")

            def get_model(filename):
                filename = filename.lstrip("/")
                path = hf_hub_download(
                    repo_id=REPO_ID, filename=filename, token=settings.HF
                )
                return load_model(path, custom_objects={"RandomShear": RandomShear})

            self.age_model = get_model("age_finetuned_model_convnext.keras")
            self.age_regression_model = get_model(
                "age_convnext_finetuned_regression_model.keras"
            )
            self.gender_model = get_model("gender/gender_base_model_convnext_op.keras")
            self.haircolor_model = get_model("haircolor_best_model_convnext.keras")
            self.hairstyle_model = get_model("hairstyle_best_model_inception.keras")
            self.eyebrows_model = get_model("eyebrows_best_model_convnext.keras")
            self.skin_model = get_model("skin_best_model_inception.keras")
            self.beard_model = get_model("beard_best_model_convnext.keras")

            # --- ส่วนของ Model Warm-up ---
            print("[INFO] Warming up models with dummy data...")
            try:
                dummy_input_224 = np.zeros((1, 224, 224, 3), dtype=np.float32)
                dummy_input_299 = np.zeros((1, 299, 299, 3), dtype=np.float32)

                self.age_model(dummy_input_224, training=False)
                self.age_regression_model(dummy_input_224, training=False)
                self.gender_model(dummy_input_224, training=False)
                self.haircolor_model(dummy_input_224, training=False)
                self.hairstyle_model(dummy_input_299, training=False)
                self.eyebrows_model(dummy_input_224, training=False)
                self.skin_model(dummy_input_299, training=False)
                self.beard_model(dummy_input_224, training=False)

                print("[SUCCESS] Warm-up complete! System is ready for fast response.")
            except Exception as e:
                print(f"[WARNING] Warm-up failed: {e}")

            self.is_loaded = True
            print("All models loaded successfully!")

    def get_preprocessed_images(self, image_bytes: bytes):
        """
        1. ทำ Face Alignment และ Crop เฉพาะใบหน้า
            2. Resize และเตรียมรูปสำหรับโมเดลต่างๆ โดยใช้ OpenCV
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_raw = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_raw is None:
            raise ValueError("ไม่สามารถอ่านไฟล์รูปภาพได้ กรุณาตรวจสอบไฟล์ที่อัปโหลด")

        img_processed = self._align_and_crop_face(img_raw)

        if img_processed is None or img_processed.size == 0:
            raise ValueError("ไม่พบใบหน้าในรูปภาพ กรุณาอัปโหลดรูปที่เห็นใบหน้าชัดเจน")

        img_rgb = cv2.cvtColor(img_processed, cv2.COLOR_BGR2RGB)

        img_224 = cv2.resize(
            img_rgb, (224, 224), interpolation=cv2.INTER_LINEAR
        ).astype(np.float32)
        img_224 = np.expand_dims(img_224, axis=0)

        img_299 = cv2.resize(
            img_rgb, (299, 299), interpolation=cv2.INTER_LINEAR
        ).astype(np.float32)
        img_299 = np.expand_dims(img_299, axis=0)

        return {
            "convnext": convnext_preprocess(img_224.copy()),
            "inception": inception_preprocess(img_299.copy()),
            "efficientnet": efficientnet_preprocess(img_224.copy()),
            "default": img_224 / 255.0,
            "raw_224": img_224,
            "raw_299": img_299,
        }

    def _map_age_to_range(self, age: float) -> list:
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
        pred = self.age_regression_model(processed_image, training=False).numpy()
        pred_age = pred[0][0]
        return self._map_age_to_range(pred_age)

    def _predict_age(self, processed_image):
        pred_probs = self.age_model(processed_image, training=False).numpy()[0]
        predicted_index = np.argmax(pred_probs)
        result = [0] * len(pred_probs)
        result[predicted_index] = 1
        return result

    def _predict_gender(self, processed_image):
        pred_prob = self.gender_model(processed_image, training=False).numpy()[0][0]
        return [0, 1] if pred_prob > 0.5 else [1, 0]

    def _predict_haircolor(self, processed_image):
        pred_probs = self.haircolor_model(processed_image, training=False).numpy()[0]
        predicted_index = np.argmax(pred_probs)
        result = [0] * len(pred_probs)
        result[predicted_index] = 1
        return result

    def _predict_hairstyle(self, processed_image):
        pred_probs = self.hairstyle_model(processed_image, training=False).numpy()[0]
        predicted_index = np.argmax(pred_probs)
        if predicted_index == 0:
            return [0, 0, 1] # ศีรษะล้าน
        elif predicted_index == 1:
            return [1, 0, 0] # ผมตรง
        else:
            return [0, 1, 0] # ผมหยักศก

    def _predict_eyebrows(self, processed_image):
        pred_probs = self.eyebrows_model(processed_image, training=False).numpy()[0]
        return (pred_probs > 0.5).astype(int).tolist()

    def _predict_skin(self, processed_image):
        pred_probs = self.skin_model(processed_image, training=False).numpy()[0]
        predicted_index = np.argmax(pred_probs)
        result = [0] * len(pred_probs)
        result[predicted_index] = 1
        return result

    def _predict_beard(self, processed_image):
        pred_probs = self.beard_model(processed_image, training=False).numpy()[0]
        return (pred_probs > 0.5).astype(int).tolist()

    def _run_predictions(self, preprocessed):
        """
        รันทุกโมเดลทีละตัวแบบเรียงลำดับ (Sequential)
        ฟังก์ชันนี้จะทำงานอยู่บน Worker Thread เดียว ไม่สร้างความภาระสลับเธรด
        """
        hairstyle_res = self._predict_hairstyle(preprocessed["inception"])
        if hairstyle_res == [0, 0, 1] or hairstyle_res == [0, 0]:
            num_haircolor_classes = self.haircolor_model.output_shape[-1]
            haircolor_res = [0] * num_haircolor_classes
        else:
            haircolor_res = self._predict_haircolor(preprocessed["convnext"])

        res_age = self._predict_age_regression(preprocessed["convnext"])
        res_gender = self._predict_gender(preprocessed["convnext"])
        res_eyebrows = self._predict_eyebrows(preprocessed["convnext"])
        res_skin = self._predict_skin(preprocessed["inception"])
        res_beard = self._predict_beard(preprocessed["convnext"])

        return {
            "age_result": res_age,
            "gender_result": res_gender,
            "haircolor_result": haircolor_res,
            "hairstyle_result": hairstyle_res,
            "eyebrows_result": res_eyebrows,
            "skin_result": res_skin,
            "beard_result": res_beard,
        }

    async def predict_all(self, image_bytes: bytes) -> dict:
        """
        ฟังก์ชันหลักที่ API เรียกใช้งาน
        """
        loop = asyncio.get_running_loop()

        preprocessed = await loop.run_in_executor(
            self.executor, self.get_preprocessed_images, image_bytes
        )

        results = await loop.run_in_executor(
            self.executor, self._run_predictions, preprocessed
        )

        return results


predictor_service = MultiModelPredictor()
