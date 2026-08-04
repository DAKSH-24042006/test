"""
Anti-Spoofing Service — Production-Grade Passive Liveness Detection

Implements multiple anti-spoofing layers:
1. MiniFASNet ONNX Model: Deep learning-based texture analysis (print/replay attack detection)
2. Moiré Pattern Detection: FFT-based frequency analysis (screen replay defense)
3. Multi-Frame Consistency: Variance analysis across frames (static image/video detection)
4. Reflection/Glare Analysis: Specular highlight detection (screen/paper gloss)
5. Face Depth Estimation: Landmark geometry 3D depth cues (flat image detection)
"""

import cv2
import numpy as np
import logging
import os
from typing import List, Tuple, Dict, Any, Optional

from backend.app.database.connection import settings

logger = logging.getLogger("anti_spoofing_service")

# ============================================================
# MiniFASNet ONNX Anti-Spoofing Model Loader
# ============================================================

ANTI_SPOOF_MODEL = None
ANTI_SPOOF_AVAILABLE = False

def _get_model_dir() -> str:
    """Returns the directory for anti-spoofing ONNX models."""
    model_dir = os.path.join(os.path.expanduser("~"), ".insightface", "anti_spoofing")
    os.makedirs(model_dir, exist_ok=True)
    return model_dir


def _load_anti_spoof_model():
    """
    Attempts to load the MiniFASNet ONNX model for passive anti-spoofing.
    If the model file is not found, the system falls back to heuristic-only mode.
    """
    global ANTI_SPOOF_MODEL, ANTI_SPOOF_AVAILABLE

    try:
        import onnxruntime as ort

        model_dir = _get_model_dir()
        # Look for any .onnx file in the model directory
        onnx_files = [f for f in os.listdir(model_dir) if f.endswith('.onnx')]

        if onnx_files:
            model_path = os.path.join(model_dir, onnx_files[0])
            ANTI_SPOOF_MODEL = ort.InferenceSession(
                model_path,
                providers=['CPUExecutionProvider']
            )
            ANTI_SPOOF_AVAILABLE = True
            logger.info(f"MiniFASNet anti-spoofing model loaded: {onnx_files[0]}")
        else:
            logger.warning(
                f"No ONNX anti-spoofing model found in {model_dir}. "
                f"Place a MiniFASNet .onnx model file there for deep learning anti-spoofing. "
                f"Falling back to heuristic-based anti-spoofing."
            )
    except ImportError:
        logger.warning("onnxruntime not installed. Anti-spoofing will use heuristics only.")
    except Exception as e:
        logger.warning(f"Failed to load anti-spoofing ONNX model: {e}. Using heuristic fallback.")


# Initialize on module load
_load_anti_spoof_model()


class AntiSpoofingService:
    """
    Production-grade anti-spoofing service combining deep learning (MiniFASNet)
    with multiple heuristic layers for defense-in-depth.
    """

    # ================================================================
    # LAYER 1: MiniFASNet Deep Learning Passive Liveness
    # ================================================================

    def classify_with_model(self, face_crop: np.ndarray) -> Tuple[bool, float, str]:
        """
        Runs the MiniFASNet ONNX model on a face crop.
        Returns: (is_live, confidence, label)
        
        The model outputs a 3-class softmax: [live, print_attack, replay_attack]
        """
        if not ANTI_SPOOF_AVAILABLE or ANTI_SPOOF_MODEL is None:
            # Fallback: return True with medium confidence when model is unavailable
            return True, 0.85, "model_unavailable_heuristic_only"

        try:
            # Preprocess: resize to 80x80, normalize to [0,1], NCHW format
            resized = cv2.resize(face_crop, (80, 80))
            blob = resized.astype(np.float32) / 255.0
            blob = np.transpose(blob, (2, 0, 1))  # HWC -> CHW
            blob = np.expand_dims(blob, axis=0)     # Add batch dimension: NCHW

            input_name = ANTI_SPOOF_MODEL.get_inputs()[0].name
            output = ANTI_SPOOF_MODEL.run(None, {input_name: blob})

            # Softmax output: [live, print_attack, replay_attack]
            scores = output[0][0]
            if len(scores) >= 3:
                live_score = float(scores[0])
                print_score = float(scores[1])
                replay_score = float(scores[2])
            elif len(scores) == 2:
                live_score = float(scores[1])
                print_score = float(scores[0])
                replay_score = 0.0
            else:
                live_score = float(scores[0])
                print_score = 1.0 - live_score
                replay_score = 0.0

            # Determine classification
            spoof_score = print_score + replay_score
            is_live = live_score > settings.ANTI_SPOOF_THRESHOLD

            if print_score > replay_score and not is_live:
                label = "print_attack"
            elif replay_score > print_score and not is_live:
                label = "replay_attack"
            elif is_live:
                label = "live"
            else:
                label = "spoof_suspected"

            return is_live, live_score, label

        except Exception as e:
            logger.error(f"MiniFASNet inference error: {e}")
            return True, 0.5, "model_error_fallback"

    # ================================================================
    # LAYER 2: Moiré Pattern Detection (Screen Replay Defense)
    # ================================================================

    def detect_moire_pattern(self, img: np.ndarray) -> Tuple[bool, float]:
        """
        Detects moiré patterns using FFT frequency analysis.
        Screens display images through pixel grids, creating periodic patterns
        visible in the frequency domain that real faces don't exhibit.
        
        Returns: (has_moire, moire_score)
        Higher moire_score = more likely a screen replay.
        """
        if not settings.MOIRE_DETECTION_ENABLED:
            return False, 0.0

        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply FFT
            f_transform = np.fft.fft2(gray.astype(np.float32))
            f_shift = np.fft.fftshift(f_transform)
            magnitude = np.log1p(np.abs(f_shift))

            h, w = magnitude.shape
            cy, cx = h // 2, w // 2

            # Create masks for different frequency bands
            # Moiré patterns appear as periodic peaks in the high-frequency band
            total_energy = np.sum(magnitude)
            if total_energy == 0:
                return False, 0.0

            # High-frequency ring (where moiré patterns manifest)
            mask_high = np.zeros_like(magnitude, dtype=bool)
            Y, X = np.ogrid[:h, :w]
            r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
            inner_r = min(h, w) * 0.25
            outer_r = min(h, w) * 0.45
            mask_high = (r >= inner_r) & (r <= outer_r)

            high_freq_energy = np.sum(magnitude[mask_high])
            high_freq_ratio = high_freq_energy / total_energy

            # Detect periodic peaks in the high-frequency band
            high_freq_region = magnitude.copy()
            high_freq_region[~mask_high] = 0

            # Threshold for peak detection
            peak_threshold = np.mean(high_freq_region[mask_high]) + 3.0 * np.std(high_freq_region[mask_high])
            peak_count = np.sum(high_freq_region > peak_threshold)

            # Moiré patterns create multiple symmetric sharp peaks in high frequencies.
            # Real camera images have high-frequency content from hair/skin, but NOT sharp periodic peaks.
            peak_score = min(1.0, peak_count / 150.0)
            has_moire = peak_count >= 120 and peak_score > 0.80
            moire_score = peak_score if has_moire else peak_score * 0.4

            if has_moire:
                logger.info(f"Moiré pattern detected: score={moire_score:.3f}, peaks={peak_count}")

            return has_moire, moire_score

        except Exception as e:
            logger.error(f"Moiré detection error: {e}")
            return False, 0.0

    # ================================================================
    # LAYER 3: Multi-Frame Consistency Analysis
    # ================================================================

    def analyze_frame_consistency(self, frames: List[np.ndarray]) -> Tuple[bool, float, str]:
        """
        Analyzes variance across multiple frames to detect static/replayed content.
        Real live faces exhibit natural micro-movements (breathing, micro-saccades).
        Static photos and looped videos show unnaturally low or periodic variance.
        
        Returns: (is_consistent_with_live, variance_score, reason)
        """
        if not settings.MULTI_FRAME_CONSISTENCY_ENABLED or len(frames) < 2:
            return True, 1.0, "insufficient_frames"

        try:
            # Convert frames to grayscale and compute inter-frame differences
            grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in frames]

            # Resize all to same dimensions for comparison
            target_h, target_w = 160, 160
            grays = [cv2.resize(g, (target_w, target_h)) for g in grays]

            # Compute absolute differences between consecutive frames
            diffs = []
            for i in range(1, len(grays)):
                diff = np.abs(grays[i] - grays[i - 1])
                diffs.append(np.mean(diff))

            mean_diff = np.mean(diffs)
            std_diff = np.std(diffs)

            # Check 1: Too little movement (true frozen/synthetic image)
            if mean_diff < 0.1:
                return False, mean_diff, "static_image_suspected"

            # Check 2: Unnaturally uniform differences (looped video replay)
            if len(diffs) >= 3 and std_diff < 0.05 and mean_diff < 1.0:
                return False, std_diff, "looped_video_suspected"

            # Check 3: Compute structural similarity between first and last frame
            correlation = np.corrcoef(grays[0].flatten(), grays[-1].flatten())[0, 1]

            if correlation > 0.9999 and mean_diff < 0.2:
                return False, correlation, "near_identical_frames"

            # Natural micro-movement score (higher = more likely real)
            liveness_indicator = min(1.0, mean_diff / 5.0)

            return True, liveness_indicator, "natural_movement_detected"

        except Exception as e:
            logger.error(f"Frame consistency analysis error: {e}")
            return True, 0.5, "analysis_error"

    # ================================================================
    # LAYER 4: Reflection / Glare Analysis (Screen & Paper Defense)
    # ================================================================

    def detect_screen_reflection(self, img: np.ndarray) -> Tuple[bool, float]:
        """
        Detects flat specular highlights characteristic of screens and glossy paper.
        Screens and printed photos produce uniform glare spots; real faces have
        organic, curved specular highlights with gradual falloff.
        
        Returns: (has_suspicious_reflection, reflection_score)
        """
        try:
            # Convert to HSV and extract the Value (brightness) channel
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]

            # Find very bright spots (potential reflections)
            bright_threshold = 240
            bright_mask = v_channel > bright_threshold
            bright_ratio = np.sum(bright_mask) / v_channel.size

            if bright_ratio < 0.001:
                return False, 0.0  # No significant bright spots

            # Analyze the shape of bright regions
            # Screen reflections tend to be rectangular/uniform
            # Face reflections are organic and scattered
            bright_regions = (v_channel > bright_threshold).astype(np.uint8) * 255
            contours, _ = cv2.findContours(bright_regions, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return False, 0.0

            # Check for large, compact rectangular bright regions (screen glare signature)
            suspicious_count = 0
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 100:
                    continue

                # Compute solidity (ratio of contour area to convex hull area)
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                if hull_area > 0:
                    solidity = area / hull_area
                else:
                    continue

                # Compute aspect ratio of bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                aspect = max(w, h) / (min(w, h) + 1e-6)

                # Screen reflections are typically high-solidity, low-aspect-ratio large bright regions
                if solidity > 0.88 and aspect < 2.5 and area > 1000:
                    suspicious_count += 1

            has_suspicious = suspicious_count >= 2
            reflection_score = min(1.0, suspicious_count / 2.0)

            return has_suspicious, reflection_score

        except Exception as e:
            logger.error(f"Reflection analysis error: {e}")
            return False, 0.0

    # ================================================================
    # LAYER 5: Face Depth Estimation via Landmark Geometry
    # ================================================================

    def estimate_face_depth(self, face_obj: Any) -> Tuple[bool, float]:
        """
        Uses InsightFace landmark geometry to estimate 3D depth cues.
        Real faces have natural depth ratios between landmarks (eyes, nose, mouth).
        Flat images (screens/printed photos) distort these ratios when viewed at angles.
        
        Returns: (has_natural_depth, depth_score)
        """
        try:
            kps = getattr(face_obj, 'kps', None)
            if kps is None or len(kps) < 5:
                return True, 0.5  # Can't evaluate without landmarks

            # 5 keypoints: [left_eye, right_eye, nose, left_mouth, right_mouth]
            left_eye = np.array(kps[0])
            right_eye = np.array(kps[1])
            nose = np.array(kps[2])
            left_mouth = np.array(kps[3])
            right_mouth = np.array(kps[4])

            # Compute geometric ratios that differ between 3D faces and flat images
            eye_dist = np.linalg.norm(right_eye - left_eye)
            if eye_dist < 1.0:
                return True, 0.5

            # Ratio: nose-to-eye-center vs eye distance
            eye_center = (left_eye + right_eye) / 2
            nose_to_eye_center = np.linalg.norm(nose - eye_center)
            ratio_nose_eye = nose_to_eye_center / eye_dist

            # Ratio: mouth-center-to-nose vs eye distance
            mouth_center = (left_mouth + right_mouth) / 2
            nose_to_mouth = np.linalg.norm(mouth_center - nose)
            ratio_mouth_nose = nose_to_mouth / eye_dist

            # Ratio: mouth width vs eye distance
            mouth_width = np.linalg.norm(right_mouth - left_mouth)
            ratio_mouth_width = mouth_width / eye_dist

            # Natural human face proportions (approximate golden ratio relationships)
            # These ratios are relatively stable for real 3D faces but distort
            # when a flat image is viewed from an angle
            natural_nose_eye = (0.35, 0.90)       # Expected range
            natural_mouth_nose = (0.25, 0.75)      # Expected range
            natural_mouth_width = (0.60, 1.30)     # Expected range

            score = 1.0
            if not (natural_nose_eye[0] <= ratio_nose_eye <= natural_nose_eye[1]):
                score -= 0.3
            if not (natural_mouth_nose[0] <= ratio_mouth_nose <= natural_mouth_nose[1]):
                score -= 0.3
            if not (natural_mouth_width[0] <= ratio_mouth_width <= natural_mouth_width[1]):
                score -= 0.3

            score = max(0.0, score)
            has_natural_depth = score > 0.5

            return has_natural_depth, score

        except Exception as e:
            logger.error(f"Depth estimation error: {e}")
            return True, 0.5

    # ================================================================
    # COMBINED ANTI-SPOOFING PIPELINE
    # ================================================================

    def run_full_pipeline(
        self,
        frames: List[np.ndarray],
        face_objects: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Runs the complete anti-spoofing pipeline on a set of frames.
        
        Returns a comprehensive result dict:
        {
            "is_live": bool,
            "overall_score": float,
            "model_result": {"is_live": bool, "confidence": float, "label": str},
            "moire_result": {"detected": bool, "score": float},
            "consistency_result": {"is_live": bool, "score": float, "reason": str},
            "reflection_result": {"detected": bool, "score": float},
            "depth_result": {"natural": bool, "score": float},
            "rejection_reasons": [str]
        }
        """
        result = {
            "is_live": True,
            "overall_score": 1.0,
            "rejection_reasons": [],
        }

        scores = []
        rejections = []

        # --- Layer 1: MiniFASNet Model (on the best frame) ---
        best_frame = frames[len(frames) // 2]  # Use middle frame (most likely well-posed)
        model_live, model_conf, model_label = self.classify_with_model(best_frame)
        result["model_result"] = {
            "is_live": model_live,
            "confidence": model_conf,
            "label": model_label,
        }
        scores.append(model_conf)
        if not model_live and model_label != "model_unavailable_heuristic_only":
            rejections.append(f"Anti-spoof model detected {model_label} (confidence: {model_conf:.2f})")

        # --- Layer 2: Moiré Pattern Detection (on multiple frames) ---
        moire_scores = []
        for frame in frames[:3]:  # Check first 3 frames
            has_moire, m_score = self.detect_moire_pattern(frame)
            moire_scores.append(m_score)
            if has_moire:
                rejections.append(f"Moiré pattern detected (score: {m_score:.2f}) — possible screen replay")
                break

        avg_moire = np.mean(moire_scores) if moire_scores else 0.0
        result["moire_result"] = {
            "detected": avg_moire > 0.65,
            "score": avg_moire,
        }
        scores.append(1.0 - avg_moire)

        # --- Layer 3: Multi-Frame Consistency ---
        consistency_live, consistency_score, consistency_reason = self.analyze_frame_consistency(frames)
        result["consistency_result"] = {
            "is_live": consistency_live,
            "score": consistency_score,
            "reason": consistency_reason,
        }
        scores.append(consistency_score)
        if not consistency_live:
            rejections.append(f"Frame consistency check failed: {consistency_reason}")

        # --- Layer 4: Reflection/Glare Analysis (on best frame) ---
        has_reflection, reflection_score = self.detect_screen_reflection(best_frame)
        result["reflection_result"] = {
            "detected": has_reflection,
            "score": reflection_score,
        }
        scores.append(1.0 - reflection_score)
        if has_reflection:
            rejections.append(f"Suspicious screen/paper reflection detected (score: {reflection_score:.2f})")

        # --- Layer 5: Depth Estimation (if face objects available) ---
        if face_objects and len(face_objects) > 0:
            best_face = face_objects[len(face_objects) // 2]
            has_depth, depth_score = self.estimate_face_depth(best_face)
            result["depth_result"] = {
                "natural": has_depth,
                "score": depth_score,
            }
            scores.append(depth_score)
            if not has_depth:
                rejections.append(f"Unnatural face depth geometry (score: {depth_score:.2f})")
        else:
            result["depth_result"] = {"natural": True, "score": 0.5}

        # --- Compute Overall Score & Decision ---
        result["overall_score"] = float(np.mean(scores)) if scores else 0.5
        result["rejection_reasons"] = rejections

        if ANTI_SPOOF_AVAILABLE and ANTI_SPOOF_MODEL is not None:
            # When ONNX deep-learning model is available, use model decision + heuristics
            result["is_live"] = model_live and (result["overall_score"] >= 0.45)
        else:
            # Heuristic-only mode: pass if overall composite score meets threshold
            result["is_live"] = result["overall_score"] >= 0.45

        if not result["is_live"]:
            logger.warning(f"Anti-spoofing rejected: score={result['overall_score']:.3f}, reasons={rejections}")
        else:
            logger.info(f"Anti-spoofing passed: overall_score={result['overall_score']:.3f}")

        return result
