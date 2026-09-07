import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import FileResponse, Response

import time
import hashlib
from backend.config import UPLOADS_DIR, PERSON_CAPTURES_DIR, PERSON_CONFIDENCE_THRESHOLD, EXPORTS_DIR
from backend.pipeline.face_processor import FaceProcessor

router = APIRouter(prefix="/api/persons", tags=["Persons"])
face_processor = FaceProcessor()

@router.post("/detect")
async def detect_persons(request: Request, file: UploadFile = File(...)):
    """Detect persons in uploaded evidence image (source='uploaded', RED boxes)"""
    t0 = time.time()
    file_id = f"EVID-{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(UPLOADS_DIR, f"{file_id}_{file.filename}")
    
    content = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(content)
        
    file_hash = hashlib.sha256(content).hexdigest()
    detector = request.app.state.person_detector
    detections = detector.detect_persons(image_path=file_path, confidence_threshold=PERSON_CONFIDENCE_THRESHOLD)
    
    annotated_bytes = detector.draw_annotated_image(content, detections, source_type='uploaded')
    annotated_path = os.path.join(UPLOADS_DIR, f"annotated_{file_id}.jpg")
    with open(annotated_path, "wb") as f:
        f.write(annotated_bytes)
        
    db = request.app.state.db
    now = datetime.now().isoformat()
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    try:
        det_id = f"PDET-{uuid.uuid4().hex[:8]}"
        conn.execute("""
            INSERT INTO person_detections (id, source_image, detection_count, timestamp, bboxes_json, confidence_scores_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (det_id, annotated_path, len(detections), now, json.dumps([d["bbox"] for d in detections]), json.dumps([d["confidence"] for d in detections])))
        conn.commit()
    finally:
        conn.close()
        
    import cv2
    import numpy as np
    img_arr = np.frombuffer(content, np.uint8)
    decoded = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
    img_h, img_w = decoded.shape[:2] if decoded is not None else (720, 1280)
    
    persons = []
    for idx, d in enumerate(detections):
        x1, y1, x2, y2 = d["bbox"]
        w = max(0, x2 - x1)
        h = max(0, y2 - y1)
        area_pct = round((w * h) / (max(1, img_w * img_h)) * 100, 2)
        persons.append({
            "person_index": idx + 1,
            "bounding_box": {"x": x1, "y": y1, "width": w, "height": h},
            "confidence": round(float(d["confidence"]), 4),
            "source": "uploaded",
            "area_percentage": area_pct,
            "timestamp": now
        })
        
    # Extract target embeddings (head/upper body and full body) from uploaded evidence to track in Live Camera
    target_embedding = None
    target_head_emb = None
    if decoded is not None:
        if detections:
            x1, y1, x2, y2 = detections[0]["bbox"]
            full_crop = decoded[max(0, y1):min(img_h, y2), max(0, x1):min(img_w, x2)]
            head_h = max(16, int((min(img_h, y2) - max(0, y1)) * 0.45))
            head_crop = decoded[max(0, y1):max(0, y1) + head_h, max(0, x1):min(img_w, x2)]
            target_embedding = face_processor.compute_embedding_from_crop(full_crop)
            target_head_emb = face_processor.compute_embedding_from_crop(head_crop)
        else:
            faces = face_processor.detect_faces(file_path)
            if faces:
                f = faces[0]
                crop = decoded[f["top"]:f["bottom"], f["left"]:f["right"]]
                target_embedding = face_processor.compute_embedding_from_crop(crop)
                target_head_emb = target_embedding
            else:
                target_embedding = face_processor.compute_embedding_from_crop(decoded)
                target_head_emb = target_embedding

    if target_embedding is not None:
        request.app.state.active_target_person = {
            "target_id": file_id,
            "file_name": file.filename,
            "file_path": file_path,
            "sha256_hash": file_hash,
            "embedding": target_embedding.tolist() if hasattr(target_embedding, "tolist") else list(target_embedding),
            "head_embedding": target_head_emb.tolist() if target_head_emb is not None and hasattr(target_head_emb, "tolist") else (list(target_head_emb) if target_head_emb is not None else None),
            "timestamp": now,
            "total_persons": len(persons)
        }

    return {
        "status": "success",
        "detection_id": det_id,
        "source_type": "uploaded",
        "image_width": img_w,
        "image_height": img_h,
        "persons": persons,
        "total_persons": len(persons),
        "count": len(persons),
        "target_set": target_embedding is not None,
        "processing_time_ms": round((time.time() - t0) * 1000, 1),
        "file_name": file.filename,
        "sha256_hash": file_hash,
        "timestamp": now
    }

@router.get("/target")
async def get_active_target(request: Request):
    """Retrieve currently active target suspect for live surveillance matching"""
    target = getattr(request.app.state, 'active_target_person', None)
    if not target:
        return {"active": False, "target": None}
    return {
        "active": True,
        "target": {
            "target_id": target.get("target_id"),
            "file_name": target.get("file_name"),
            "sha256_hash": target.get("sha256_hash"),
            "timestamp": target.get("timestamp")
        }
    }

@router.post("/target/clear")
async def clear_active_target(request: Request):
    """Clear currently active target suspect"""
    request.app.state.active_target_person = None
    return {"status": "success", "message": "Active target cleared"}

@router.post("/detect-frame")
async def detect_frame(request: Request, file: UploadFile = File(None), frame: UploadFile = File(None)):
    """Fast detection on live webcam frame with real-time target matching (GREEN/RED alert boxes)"""
    upload = frame or file
    if upload is None:
        raise HTTPException(status_code=400, detail="No frame uploaded")
        
    t0 = time.time()
    image_data = await upload.read()
    detector = request.app.state.person_detector
    
    detections = detector.detect_persons(image_data=image_data, fast_mode=True, confidence_threshold=PERSON_CONFIDENCE_THRESHOLD)
    now = datetime.now().isoformat()
    
    active_target = getattr(request.app.state, 'active_target_person', None)
    target_matched = False
    highest_sim = 0.0
    
    frame_img = None
    target_emb = None
    if active_target and detections and "embedding" in active_target:
        try:
            import numpy as np
            import cv2
            nparr = np.frombuffer(image_data, np.uint8)
            frame_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            target_emb = np.array(active_target["embedding"], dtype=np.float32)
        except Exception:
            pass

    persons = []
    for idx, d in enumerate(detections):
        x1, y1, x2, y2 = d["bbox"]
        w = max(0, x2 - x1)
        h = max(0, y2 - y1)
        
        is_match = False
        sim_score = 0.0
        
        if frame_img is not None and target_emb is not None:
            f_h, f_w = frame_img.shape[:2]
            x1_c = max(0, min(f_w - 1, x1))
            x2_c = max(x1_c + 1, min(f_w, x2))
            y1_c = max(0, min(f_h - 1, y1))
            y2_c = max(y1_c + 1, min(f_h, y2))
            
            # Extract head/upper body and full-body crops
            head_h = max(16, int((y2_c - y1_c) * 0.45))
            head_crop = frame_img[y1_c:y1_c + head_h, x1_c:x2_c]
            full_crop = frame_img[y1_c:y2_c, x1_c:x2_c]
            
            head_emb = face_processor.compute_embedding_from_crop(head_crop)
            full_emb = face_processor.compute_embedding_from_crop(full_crop)

            target_head_emb = None
            if "head_embedding" in active_target and active_target["head_embedding"]:
                target_head_emb = np.array(active_target["head_embedding"], dtype=np.float32)

            # Test live head vs target head & target full
            sim_head_to_head = face_processor.compare_faces(target_head_emb, head_emb) if (target_head_emb is not None and head_emb is not None) else 0.0
            sim_head_to_full = face_processor.compare_faces(target_emb, head_emb) if head_emb is not None else 0.0
            # Test live full vs target full & target head
            sim_full_to_full = face_processor.compare_faces(target_emb, full_emb) if full_emb is not None else 0.0
            sim_full_to_head = face_processor.compare_faces(target_head_emb, full_emb) if (target_head_emb is not None and full_emb is not None) else 0.0
            
            sim_score = max(sim_head_to_head, sim_head_to_full, sim_full_to_full, sim_full_to_head)
            
            # High-confidence threshold: >= 0.65 ensures ONLY the uploaded person matches,
            # completely rejecting different persons (which score ~0.20 - 0.45).
            if sim_score >= 0.65:
                is_match = True
                target_matched = True
                if sim_score > highest_sim:
                    highest_sim = sim_score

        persons.append({
            "person_index": idx + 1,
            "bounding_box": {"x": x1, "y": y1, "width": w, "height": h},
            "confidence": round(float(d["confidence"]), 4),
            "source": "live",
            "is_target_match": is_match,
            "match_similarity": round(float(sim_score) * 100, 1) if is_match else 0.0,
            "area_percentage": 0.0,
            "timestamp": now
        })
        
    return {
        "status": "success",
        "source_type": "live",
        "persons_count": len(persons),
        "persons": persons,
        "target_active": active_target is not None,
        "target_matched": target_matched,
        "highest_match_score": round(float(highest_sim) * 100, 1) if target_matched else (round(float(sim_score) * 100, 1) if active_target and persons else 0.0),
        "target_filename": active_target.get("file_name") if active_target else None,
        "processing_time_ms": round((time.time() - t0) * 1000, 1),
        "timestamp": now
    }


@router.post("/batch-detect")
async def batch_detect(request: Request, files: List[UploadFile] = File(...)):
    """Batch detect from multiple images"""
    results = []
    detector = request.app.state.person_detector
    
    for file in files:
        image_data = await file.read()
        detections = detector.detect_persons(image_data=image_data, confidence_threshold=PERSON_CONFIDENCE_THRESHOLD)
        results.append({
            "filename": file.filename,
            "count": len(detections),
            "detections": detections
        })
        
    return {"status": "success", "results": results}

@router.post("/capture")
async def capture_frame(request: Request, file: UploadFile = File(None), frame: UploadFile = File(None)):
    """Save captured live frame with blockchain seal"""
    upload = frame or file
    if upload is None:
        raise HTTPException(status_code=400, detail="No frame uploaded")
        
    image_data = await upload.read()
    detector = request.app.state.person_detector
    
    detections = detector.detect_persons(image_data=image_data, fast_mode=True, confidence_threshold=PERSON_CONFIDENCE_THRESHOLD)
    annotated_bytes = detector.draw_annotated_image(image_data, detections, source_type='live')
    
    cap_id = f"CAP-{uuid.uuid4().hex[:8]}"
    cap_path = os.path.join(PERSON_CAPTURES_DIR, f"{cap_id}.jpg")
    
    with open(cap_path, "wb") as f:
        f.write(annotated_bytes)
        
    file_hash = hashlib.sha256(annotated_bytes).hexdigest()
    blockchain = request.app.state.blockchain
    blockchain.add_block(file_hash, f"{cap_id}.jpg", "image/jpeg", "SYSTEM")
    
    db = request.app.state.db
    now = datetime.now().isoformat()
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    try:
        conn.execute("""
            INSERT INTO person_captures (id, capture_path, detection_count, timestamp, blockchain_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (cap_id, cap_path, len(detections), now, file_hash))
        conn.commit()
    finally:
        conn.close()
        
    return {"status": "success", "capture_id": cap_id, "blockchain_hash": file_hash}

@router.get("/history")
async def get_history(request: Request):
    """List detection history"""
    db = request.app.state.db
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("SELECT * FROM person_detections ORDER BY timestamp DESC LIMIT 100")
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
    return rows

@router.get("/export-log")
async def export_log(request: Request):
    """Export detection log as CSV"""
    import csv
    db = request.app.state.db
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("SELECT * FROM person_detections ORDER BY timestamp DESC")
        rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
        
    csv_path = os.path.join(EXPORTS_DIR, "person_detections.csv")
    with open(csv_path, "w", newline='') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=["id", "source_image", "detection_count", "timestamp", "bboxes_json", "confidence_scores_json"])
            writer.writeheader()
            writer.writerows(rows)
        else:
            writer = csv.writer(f)
            writer.writerow(["id", "source_image", "detection_count", "timestamp", "bboxes_json", "confidence_scores_json"])
        
    return FileResponse(csv_path, filename="person_detections.csv")

@router.get("/annotated/{detection_id}")
async def get_annotated_image(request: Request, detection_id: str):
    """Serve pre-annotated image"""
    db = request.app.state.db
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("SELECT source_image FROM person_detections WHERE id = ?", (detection_id,))
        row = cursor.fetchone()
        if not row or not os.path.exists(row["source_image"]):
            raise HTTPException(status_code=404, detail="Annotated image not found")
        return FileResponse(row["source_image"])
    finally:
        conn.close()
