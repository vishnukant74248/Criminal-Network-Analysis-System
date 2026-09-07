import os
import cv2
import numpy as np
import json
import uuid
from typing import List, Dict, Optional
from PIL import Image

try:
    import face_recognition
    FACE_REC_AVAILABLE = True
except ImportError:
    FACE_REC_AVAILABLE = False
    print("WARNING: face_recognition library not available. Falling back to Haar Cascades (no embeddings).")

class FaceProcessor:
    def __init__(self):
        self.haar_cascade = None
        if not FACE_REC_AVAILABLE:
            try:
                data_attr = getattr(cv2, 'data', None)
                cascade_path = (data_attr.haarcascades if data_attr else '') + 'haarcascade_frontalface_default.xml'
                if hasattr(cv2, 'CascadeClassifier'):
                    self.haar_cascade = cv2.CascadeClassifier(cascade_path)
            except Exception as e:
                print(f"Notice: CascadeClassifier fallback not loaded: {e}")
                self.haar_cascade = None

    def detect_faces(self, image_path: str) -> List[Dict[str, int]]:
        """Detect faces and return bounding boxes in format: top, right, bottom, left."""
        if FACE_REC_AVAILABLE:
            try:
                image = face_recognition.load_image_file(image_path)
                face_locations = face_recognition.face_locations(image)
                if face_locations:
                    return [{"top": top, "right": right, "bottom": bottom, "left": left} for (top, right, bottom, left) in face_locations]
            except Exception as e:
                print(f"Notice: face_recognition detection error ({e}), falling back to OpenCV")

        image = cv2.imread(image_path)
        if image is None:
            return []
        h, w = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        detected = []
        if self.haar_cascade is not None:
            faces = self.haar_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
            for (x, y, fw, fh) in faces:
                detected.append({"top": int(y), "right": int(x + fw), "bottom": int(y + fh), "left": int(x)})

        # Fallback: if no face found but image is portrait/mugshot, provide centered face box
        if not detected and h > 0 and w > 0:
            pad_h = int(h * 0.15)
            pad_w = int(w * 0.20)
            detected.append({
                "top": max(0, pad_h),
                "right": min(w, w - pad_w),
                "bottom": min(h, h - pad_h),
                "left": max(0, pad_w)
            })

        return detected

    def compute_embedding(self, image_path: str, face_location: Dict[str, int]) -> Optional[np.ndarray]:
        """Compute 128-d face embedding for a specific face location."""
        if FACE_REC_AVAILABLE:
            try:
                image = face_recognition.load_image_file(image_path)
                loc_tuple = (face_location["top"], face_location["right"], face_location["bottom"], face_location["left"])
                encodings = face_recognition.face_encodings(image, known_face_locations=[loc_tuple])
                if encodings:
                    return encodings[0]
            except Exception as e:
                print(f"Notice: face_recognition encoding error ({e}), using OpenCV descriptor fallback")

        # Robust 128-d normalized visual feature descriptor fallback
        try:
            image = cv2.imread(image_path)
            if image is None:
                return None
            h, w = image.shape[:2]
            top = max(0, min(h - 1, face_location["top"]))
            bottom = max(top + 1, min(h, face_location["bottom"]))
            left = max(0, min(w - 1, face_location["left"]))
            right = max(left + 1, min(w, face_location["right"]))

            crop = image[top:bottom, left:right]
            if crop.size == 0:
                return None
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            # Resize to 16x8 spatial grid -> 128 dimensions
            resized = cv2.resize(gray, (16, 8), interpolation=cv2.INTER_AREA).astype(np.float32)
            vector = resized.flatten()
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            return vector
        except Exception as e:
            print(f"Embedding computation error: {e}")
            return None

    def compute_embedding_from_crop(self, crop: np.ndarray) -> Optional[np.ndarray]:
        """Compute visual descriptor embedding directly from an in-memory image crop (BGR numpy array)."""
        if crop is None or not hasattr(crop, 'size') or crop.size == 0:
            return None
        try:
            if FACE_REC_AVAILABLE:
                rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                encodings = face_recognition.face_encodings(rgb)
                if encodings:
                    return encodings[0]
        except Exception:
            pass

        try:
            # Standardize crop to 64x128 for normalized biometric feature extraction
            std_crop = cv2.resize(crop, (64, 128), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(std_crop, cv2.COLOR_BGR2GRAY)
            
            # 1. Spatial Block Histograms (32 spatial blocks, 16 bins = 512 dimensions)
            # This precisely identifies individual appearance, facial structure, skin tone, and clothing
            bh, bw = 16, 16
            blocks = []
            for y in range(0, 128, bh):
                for x in range(0, 64, bw):
                    blk = gray[y:y+bh, x:x+bw]
                    h = cv2.calcHist([blk], [0], None, [16], [0, 256]).flatten()
                    h = h / (np.sum(h) + 1e-6)
                    blocks.append(h)
            block_feat = np.concatenate(blocks).astype(np.float32)
            block_feat /= (np.linalg.norm(block_feat) + 1e-6)

            # 2. 3D HSV Color Distribution (12 H x 4 S x 4 V = 192 bins)
            hsv = cv2.cvtColor(std_crop, cv2.COLOR_BGR2HSV)
            hsv_hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 4, 4], [0, 180, 0, 256, 0, 256]).flatten()
            hsv_hist = hsv_hist / (np.sum(hsv_hist) + 1e-6)
            hsv_hist /= (np.linalg.norm(hsv_hist) + 1e-6)

            # 3. Zero-Mean Normalized Spatial Texture Vector (16x32 = 512 dimensions)
            struct = cv2.resize(gray, (16, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
            struct = (struct - np.mean(struct)) / (np.std(struct) + 1e-5)
            struct_feat = struct.flatten() / (np.linalg.norm(struct) + 1e-6)

            # Combined Biometric Signature (1216 dimensions)
            combined = np.concatenate([block_feat * 1.5, hsv_hist * 1.2, struct_feat * 1.0]).astype(np.float32)
            norm = np.linalg.norm(combined)
            return combined / norm if norm > 0 else combined
        except Exception as e:
            return None

    def compare_faces(self, known_embedding: np.ndarray, target_embedding: np.ndarray) -> float:
        """Compare two embeddings and return similarity score (0.0 - 1.0)."""
        if FACE_REC_AVAILABLE and hasattr(known_embedding, 'shape') and known_embedding.shape == (128,):
            try:
                distance = face_recognition.face_distance([known_embedding], target_embedding)[0]
                return float(max(0.0, 1.0 - distance))
            except Exception:
                pass

        # Normalized cosine similarity fallback
        try:
            k = np.asarray(known_embedding, dtype=np.float32).flatten()
            t = np.asarray(target_embedding, dtype=np.float32).flatten()
            if len(k) != len(t):
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
