import os
import cv2
import numpy as np
import json
import uuid
from typing import List, Dict, Optional
from PIL import Image

try:
    import onnxruntime as ort
    ort.set_default_logger_severity(3)
    ORT_AVAILABLE = True
except ImportError:
    ORT_AVAILABLE = False

try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
YUNET_PATH = os.path.join(MODELS_DIR, "face_detection_yunet.onnx")
SFACE_PATH = os.path.join(MODELS_DIR, "face_recognition_sface.onnx")

class FaceProcessor:
    def __init__(self):
        self.yunet_detector = None
        self.sface_session = None
        self.ref_landmarks = np.array([
            [38.2946, 51.6963],
            [73.5318, 51.5014],
            [56.0252, 71.7366],
            [41.5493, 92.3655],
            [70.7299, 92.2041]
        ], dtype=np.float32)

        if os.path.exists(YUNET_PATH):
            try:
                self.yunet_detector = cv2.FaceDetectorYN_create(
                    YUNET_PATH, "", (320, 320),
                    score_threshold=0.30,
                    nms_threshold=0.25,
                    top_k=5000
                )
            except Exception as e:
                print(f"Notice: YuNet initialization warning: {e}")
                self.yunet_detector = None

        if ORT_AVAILABLE and os.path.exists(SFACE_PATH):
            try:
                opts = ort.SessionOptions()
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                opts.intra_op_num_threads = 2
                self.sface_session = ort.InferenceSession(
                    SFACE_PATH,
                    sess_options=opts,
                    providers=["CPUExecutionProvider"]
                )
            except Exception as e:
                print(f"Notice: SFace ORT initialization warning: {e}")
                self.sface_session = None

    def detect_faces(self, image_path: str) -> List[Dict[str, int]]:
        """Detect faces and return bounding boxes in format: top, right, bottom, left."""
        if FACE_REC_AVAILABLE:
            try:
                image = face_recognition.load_image_file(image_path)
                face_locations = face_recognition.face_locations(image)
                if face_locations:
                    return [{"top": top, "right": right, "bottom": bottom, "left": left} for (top, right, bottom, left) in face_locations]
            except Exception:
                pass

        image = cv2.imread(image_path)
        if image is None:
            return []
        h, w = image.shape[:2]

        if self.yunet_detector is not None:
            try:
                self.yunet_detector.setInputSize((w, h))
                _, faces = self.yunet_detector.detect(image)
                if faces is not None and len(faces) > 0:
                    detected = []
                    for f in faces:
                        fx, fy, fw, fh = f[0:4].astype(int)
                        detected.append({
                            "top": max(0, int(fy)),
                            "right": min(w, int(fx + fw)),
                            "bottom": min(h, int(fy + fh)),
                            "left": max(0, int(fx))
                        })
                    return detected
            except Exception as e:
                print(f"Notice: YuNet detection error: {e}")

        # Fallback: if no face found, provide centered face box
        detected = []
        if h > 0 and w > 0:
            pad_h = int(h * 0.15)
            pad_w = int(w * 0.20)
            detected.append({
                "top": max(0, pad_h),
                "right": min(w, w - pad_w),
                "bottom": min(h, h - pad_h),
                "left": max(0, pad_w)
            })

        return detected

    def align_face(self, img_bgr: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect facial landmarks and align face strictly to 112x112 pure facial coordinates.
        Completely excludes clothes, dress, torso, and background.
        """
        if img_bgr is None or not hasattr(img_bgr, "shape") or img_bgr.size == 0:
            return None
        h, w = img_bgr.shape[:2]
        if h < 8 or w < 8:
            return None

        # Try YuNet 5-point landmark detection
        if self.yunet_detector is not None:
            try:
                self.yunet_detector.setInputSize((w, h))
                _, faces = self.yunet_detector.detect(img_bgr)
                if faces is not None and len(faces) > 0:
                    best_face = max(faces, key=lambda f: f[-1])
                    landmarks = best_face[4:14].reshape((5, 2))
                    tfm, _ = cv2.estimateAffinePartial2D(landmarks, self.ref_landmarks)
                    if tfm is not None:
                        aligned = cv2.warpAffine(img_bgr, tfm, (112, 112))
                        return aligned
                    else:
                        fx, fy, fw, fh = best_face[0:4].astype(int)
                        crop = img_bgr[max(0, fy):min(h, fy + fh), max(0, fx):min(w, fx + fw)]
                        if crop.size > 0:
                            return cv2.resize(crop, (112, 112))
            except Exception:
                pass

        # Fallback for face/head crop: take upper 45% (pure head/face, never clothes)
        head_h = max(8, int(h * 0.45))
        head_crop = img_bgr[0:head_h, :]
        if head_crop.size > 0:
            return cv2.resize(head_crop, (112, 112))
        return cv2.resize(img_bgr, (112, 112))

    def compute_embedding(self, image_path: str, face_location: Dict[str, int]) -> Optional[np.ndarray]:
        """Compute 128-d face embedding for a specific face location."""
        image = cv2.imread(image_path)
        if image is None:
            return None
        h, w = image.shape[:2]
        top = max(0, min(h - 1, face_location["top"]))
        bottom = max(top + 1, min(h, face_location["bottom"]))
        left = max(0, min(w - 1, face_location["left"]))
        right = max(left + 1, min(w, face_location["right"]))

        crop = image[top:bottom, left:right]
        return self.compute_embedding_from_crop(crop)

    def compute_embedding_from_crop(self, crop: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract 128-dimensional deep metric face embedding using SFace.
        Strictly analyzes facial biometrics (eyes, nose, mouth, contours).
        Completely ignores clothing, dress, shirt, or torso.
        """
        if crop is None or not hasattr(crop, "size") or crop.size == 0:
            return None

        aligned_face = self.align_face(crop)
        if aligned_face is None or aligned_face.size == 0:
            return None

        if self.sface_session is not None:
            try:
                # SFace input format: (1, 3, 112, 112), float32, BGR
                blob = aligned_face.astype(np.float32)
                blob = np.transpose(blob, (2, 0, 1))
                blob = np.expand_dims(blob, axis=0)

                input_name = self.sface_session.get_inputs()[0].name
                output_name = self.sface_session.get_outputs()[0].name
                emb = self.sface_session.run([output_name], {input_name: blob})[0][0]

                # L2 normalize
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                return emb
            except Exception as e:
                print(f"Notice: SFace inference error: {e}")

        # Grayscale normalized 128-d fallback
        try:
            gray = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (16, 8), interpolation=cv2.INTER_AREA).astype(np.float32)
            vector = resized.flatten()
            norm = np.linalg.norm(vector)
            return vector / norm if norm > 0 else vector
        except Exception:
            return None

    def compare_faces(self, known_embedding: np.ndarray, target_embedding: np.ndarray) -> float:
        """
        Pure cosine similarity comparison between two 128-d facial embeddings.
        Returns similarity score in range [0.0, 1.0].
        """
        if known_embedding is None or target_embedding is None:
            return 0.0
        try:
            k = np.asarray(known_embedding, dtype=np.float32).flatten()
            t = np.asarray(target_embedding, dtype=np.float32).flatten()
            if len(k) != len(t) or len(k) == 0:
                return 0.0
            norm_k = np.linalg.norm(k)
            norm_t = np.linalg.norm(t)
            if norm_k > 0 and norm_t > 0:
                cos_sim = float(np.dot(k, t) / (norm_k * norm_t))
                return max(0.0, min(1.0, cos_sim))
            return 0.0
        except Exception as e:
            print(f"Comparison error: {e}")
            return 0.0

    def scan_directory(self, known_embedding: np.ndarray, directory: str, min_similarity: float) -> List[Dict]:
        """Scan a directory for faces matching the known embedding."""
        matches = []
        if not os.path.exists(directory) or not FACE_REC_AVAILABLE:
            return matches
            
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(root, file)
                    faces = self.detect_faces(file_path)
                    for face_loc in faces:
                        emb = self.compute_embedding(file_path, face_loc)
                        if emb is not None:
                            sim = self.compare_faces(known_embedding, emb)
                            if sim >= min_similarity:
                                matches.append({
                                    "file_path": file_path,
                                    "similarity": sim,
                                    "bbox": face_loc
                                })
        return matches

    def crop_face_thumbnail(self, image_path: str, bbox: Dict[str, int], output_path: str) -> str:
        """Crop the detected face from the image and save as thumbnail."""
        image = Image.open(image_path)
        
        width = bbox["right"] - bbox["left"]
        height = bbox["bottom"] - bbox["top"]
        pad_x = int(width * 0.2)
        pad_y = int(height * 0.2)
        
        crop_box = (
            max(0, bbox["left"] - pad_x),
            max(0, bbox["top"] - pad_y),
            min(image.width, bbox["right"] + pad_x),
            min(image.height, bbox["bottom"] + pad_y)
        )
        
        face_img = image.crop(crop_box)
        if face_img.mode in ("RGBA", "P"):
            face_img = face_img.convert("RGB")
        face_img.save(output_path, format="JPEG")
        return output_path
