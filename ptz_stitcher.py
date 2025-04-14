#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import os
from pathlib import Path
import json

class PTZStitcher:
    def __init__(self):
        # Initialize SIFT detector
        self.sift = cv2.SIFT_create()
        # Initialize FLANN matcher
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        self.matcher = cv2.FlannBasedMatcher(index_params, search_params)
        
        # Initialize storage for images and metadata
        self.images = []
        self.positions = []
        self.keypoints = []
        self.descriptors = []
        
    def load_images_with_metadata(self, image_dir, metadata_file):
        """Load images and their PTZ metadata."""
        self.images = []
        self.positions = []
        
        # Load metadata
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Load images in order
        image_dir = Path(image_dir)
        for img_info in sorted(metadata['images'], key=lambda x: x['position']):
            img_path = image_dir / img_info['filename']
            img = cv2.imread(str(img_path))
            if img is not None:
                self.images.append(img)
                self.positions.append(img_info['position'])
        
        return len(self.images)
    
    def load_images(self, image_dir):
        """Load images without metadata."""
        self.images = []
        image_dir = Path(image_dir)
        
        # Load all jpg images in the directory
        for img_path in sorted(image_dir.glob("*.jpg")):
            img = cv2.imread(str(img_path))
            if img is not None:
                self.images.append(img)
        
        return len(self.images)
    
    def detect_features(self):
        """Detect SIFT features in all loaded images."""
        self.keypoints = []
        self.descriptors = []
        
        for img in self.images:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Detect keypoints and compute descriptors
            kp, des = self.sift.detectAndCompute(gray, None)
            self.keypoints.append(kp)
            self.descriptors.append(des)
    
    def match_features(self, ratio=0.75):
        """Match features between consecutive images."""
        self.matches = []
        
        for i in range(len(self.images) - 1):
            if (self.descriptors[i] is not None and 
                self.descriptors[i+1] is not None and 
                len(self.descriptors[i]) >= 2 and 
                len(self.descriptors[i+1]) >= 2):
                
                # Find k=2 nearest matches for each descriptor
                matches = self.matcher.knnMatch(self.descriptors[i+1], self.descriptors[i], k=2)
                good_matches = []
                
                # Apply Lowe's ratio test
                for m, n in matches:
                    if m.distance < ratio * n.distance:
                        good_matches.append(m)
                
                self.matches.append(good_matches)
            else:
                self.matches.append([])
    
    def create_panorama_sift(self):
        """Create panorama using SIFT features and homography."""
        if len(self.images) < 2:
            return None
        
        # Detect and match features if not done already
        if not self.keypoints:
            self.detect_features()
        if not hasattr(self, 'matches'):
            self.match_features()
        
        # Initialize with first image
        result = self.images[0].copy()
        h_total = np.eye(3)
        
        # Get base dimensions
        base_height = result.shape[0]
        base_width = result.shape[1]
        max_width = base_width * len(self.images)  # Maximum reasonable width
        
        for i in range(len(self.matches)):
            if len(self.matches[i]) >= 4:
                # Get matching points
                src_pts = np.float32([self.keypoints[i+1][m.queryIdx].pt for m in self.matches[i]])
                dst_pts = np.float32([self.keypoints[i][m.trainIdx].pt for m in self.matches[i]])
                
                # Calculate homography
                H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                if H is not None:
                    # Update cumulative homography
                    h_total = h_total @ H
                    
                    # Calculate warped image corners
                    h, w = self.images[i+1].shape[:2]
                    corners = np.float32([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]]).reshape(-1, 1, 2)
                    warped_corners = cv2.perspectiveTransform(corners, h_total)
                    
                    # Get bounding box
                    [x_min, y_min] = np.int32(warped_corners.min(axis=0).ravel())
                    [x_max, y_max] = np.int32(warped_corners.max(axis=0).ravel())
                    
                    # Check if dimensions are reasonable
                    if x_max - x_min > max_width or y_max - y_min > base_height * 3:
                        print(f"Warning: Unreasonable dimensions detected at image {i+1}. Skipping.")
                        continue
                    
                    # Adjust transformation matrix for negative offsets
                    if x_min < 0:
                        h_total[0, 2] -= x_min
                    if y_min < 0:
                        h_total[1, 2] -= y_min
                    
                    # Calculate output dimensions
                    output_width = min(max_width, max(result.shape[1], x_max))
                    output_height = min(base_height * 3, max(result.shape[0], y_max))
                    
                    # Warp image
                    warped = cv2.warpPerspective(self.images[i+1], h_total, (output_width, output_height))
                    
                    # Create mask for blending
                    mask = np.zeros((output_height, output_width), dtype=np.uint8)
                    cv2.fillConvexPoly(mask, np.int32(warped_corners), 255)
                    
                    # Extend result if needed
                    if output_width > result.shape[1] or output_height > result.shape[0]:
                        extended = np.zeros((output_height, output_width, 3), dtype=np.uint8)
                        extended[:result.shape[0], :result.shape[1]] = result
                        result = extended
                    
                    # Blend images
                    mask = mask.astype(float) / 255
                    for c in range(3):
                        result[..., c] = result[..., c] * (1 - mask) + warped[..., c] * mask
        
        # Final crop of black borders
        if result is not None:
            gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
                result = result[y:y+h, x:x+w]
        
        return result
    
    def create_panorama_metadata(self):
        """Create panorama using PTZ metadata positions."""
        if not self.positions or len(self.images) < 2:
            return None
        
        # Find the minimum x position to normalize positions
        min_x = min(pos[0] for pos in self.positions)
        
        # Calculate normalized positions relative to leftmost image
        normalized_positions = [(pos[0] - min_x, pos[1]) for pos in self.positions]
        
        # Calculate total width needed
        max_x = max(pos[0] for pos in normalized_positions)
        base_width = max(img.shape[1] for img in self.images)
        total_width = int(max_x + base_width)  # Add width of last image
        
        # Get maximum height of all images
        max_height = max(img.shape[0] for img in self.images)
        
        # Create output panorama
        panorama = np.zeros((max_height, total_width, 3), dtype=np.uint8)
        
        # Place each image according to its normalized position
        for i, img in enumerate(self.images):
            h, w = img.shape[:2]
            
            # Calculate x position based on normalized position
            x_pos = int(normalized_positions[i][0])
            
            # Center vertically
            y_pos = (max_height - h) // 2
            
            # Ensure we don't exceed panorama bounds
            if x_pos + w > total_width:
                w = total_width - x_pos
                if w <= 0:
                    continue
                img = img[:, :w]
            
            # Copy image to panorama
            try:
                panorama[y_pos:y_pos+h, x_pos:x_pos+w] = img
            except ValueError as e:
                print(f"Warning: Could not place image {i} at position {x_pos},{y_pos}")
                continue
        
        # Remove any empty columns at the end
        gray = cv2.cvtColor(panorama, cv2.COLOR_BGR2GRAY)
        mask = gray.sum(axis=0) > 0
        if mask.any():
            first_col = mask.argmax()
            last_col = len(mask) - mask[::-1].argmax()
            panorama = panorama[:, first_col:last_col]
        
        return panorama 