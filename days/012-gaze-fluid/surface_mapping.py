"""AprilTag screen mapping for Neon scene-camera pixels.

The markers are AprilTag 36h11 IDs 0..3. Geometry is stored in display pixels,
while detections are in the Neon scene camera's pixel coordinate system.
"""
import json
import math
from pathlib import Path
import time


def load_layout(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    width, height = data["size"]
    if width <= 0 or height <= 0:
        raise ValueError("Surface size must be positive")
    markers = {}
    for key, corners in data["markers"].items():
        if len(corners) != 4 or any(len(point) != 2 for point in corners):
            raise ValueError(f"Marker {key} needs four 2D corners")
        markers[int(key)] = corners
    if len(markers) < 3:
        raise ValueError("At least three unique AprilTags are required")
    return (int(width), int(height)), markers


class SurfaceMapper:
    """Update one frame at a time; invalidate immediately when tags disappear."""
    def __init__(self, layout_path, min_tags=3, max_age=.25):
        import cv2
        from pupil_apriltags import Detector
        self.cv2 = cv2
        self.np = __import__("numpy")
        self.size, self.markers = load_layout(layout_path)
        self.detector = Detector(families="tag36h11", nthreads=2,
                                 quad_decimate=2.0, decode_sharpening=1.0)
        self.min_tags = min_tags
        self.max_age = max_age
        self.matrix = None
        self.last_frame = None
        self.marker_count = 0
        self.inlier_count = 0

    def update(self, bgr, now=None):
        now = time.monotonic() if now is None else now
        gray = self.cv2.cvtColor(bgr, self.cv2.COLOR_BGR2GRAY)
        detections = self.detector.detect(gray)
        source, target, ids = [], [], set()
        for tag in detections:
            tag_id = int(tag.tag_id)
            if tag_id not in self.markers or tag_id in ids:
                continue
            ids.add(tag_id)
            # pupil_apriltags corners: top-right, top-left, bottom-left, bottom-right.
            source.extend(tag.corners)
            tl, tr, br, bl = self.markers[tag_id]
            target.extend((tr, tl, bl, br))
        self.marker_count = len(ids)
        self.last_frame = now
        self.matrix = None
        self.inlier_count = 0
        if len(ids) < self.min_tags:
            return False
        src = self.np.asarray(source, dtype=self.np.float32)
        dst = self.np.asarray(target, dtype=self.np.float32)
        matrix, mask = self.cv2.findHomography(src, dst, self.cv2.RANSAC, 5.0)
        if matrix is None or not self.np.isfinite(matrix).all():
            return False
        self.inlier_count = int(mask.sum()) if mask is not None else 0
        if self.inlier_count < self.min_tags * 3:
            return False
        self.matrix = matrix
        return True

    def map_xy(self, x, y, now=None):
        now = time.monotonic() if now is None else now
        if self.matrix is None or self.last_frame is None or now-self.last_frame > self.max_age:
            return None
        point = self.np.asarray([[[x,y]]], dtype=self.np.float32)
        mapped = self.cv2.perspectiveTransform(point, self.matrix)[0,0]
        if not all(math.isfinite(float(v)) for v in mapped):
            return None
        return float(mapped[0]), float(mapped[1])

    @property
    def visible(self):
        return self.matrix is not None and self.last_frame is not None and time.monotonic()-self.last_frame <= self.max_age
