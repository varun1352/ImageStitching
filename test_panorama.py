#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
from pathlib import Path
import argparse
from ptz_stitcher import PTZStitcher
import time

def create_output_dir():
    """Create output directory if it doesn't exist."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    return output_dir

def main():
    parser = argparse.ArgumentParser(description="Create a panorama using different methods")
    parser.add_argument("--method", choices=['sift', 'metadata'], default='sift',
                      help="Stitching method to use")
    parser.add_argument("--no-display", action="store_true",
                      help="Don't display the result")
    parser.add_argument("--verbose", "-v", action="store_true",
                      help="Show detailed progress")
    args = parser.parse_args()
    
    # Create stitcher instance
    stitcher = PTZStitcher()
    
    # Create output directory
    output_dir = create_output_dir()
    
    start_time = time.time()
    
    # Load images based on method
    if args.method == 'metadata':
        if args.verbose:
            print("Using metadata-based stitching method...")
            print("Loading images and metadata...")
            
        num_images = stitcher.load_images_with_metadata("images", "images/metadata.json")
        if num_images < 2:
            print("Error: Not enough images found with metadata")
            return False
            
        if args.verbose:
            print(f"Successfully loaded {num_images} images with metadata")
            print("Creating panorama using metadata positions...")
            
        # Create panorama using metadata
        panorama = stitcher.create_panorama_metadata()
        output_path = output_dir / "panorama_metadata.jpg"
        
    else:  # sift
        if args.verbose:
            print("Using SIFT-based stitching method...")
            print("Loading images...")
            
        num_images = stitcher.load_images("images")
        if num_images < 2:
            print("Error: Not enough images found")
            return False
            
        if args.verbose:
            print(f"Successfully loaded {num_images} images")
            print("Detecting SIFT features...")
            
        stitcher.detect_features()
        
        if args.verbose:
            total_keypoints = sum(len(kp) for kp in stitcher.keypoints)
            print(f"Found {total_keypoints} total keypoints across all images")
            print(f"Average {total_keypoints // num_images} keypoints per image")
            print("Matching features between consecutive images...")
            
        stitcher.match_features()
        
        if args.verbose:
            total_matches = sum(len(m) for m in stitcher.matches)
            print(f"Found {total_matches} total good matches between image pairs")
            print("Creating panorama using SIFT features...")
            
        # Create panorama using SIFT
        panorama = stitcher.create_panorama_sift()
        output_path = output_dir / "panorama_sift.jpg"
    
    if panorama is None:
        print("Error: Failed to create panorama")
        return False
        
    # Save the result
    cv2.imwrite(str(output_path), panorama)
    
    end_time = time.time()
    if args.verbose:
        print(f"\nPanorama creation completed in {end_time - start_time:.2f} seconds")
        print(f"Output dimensions: {panorama.shape[1]}x{panorama.shape[0]} pixels")
        print(f"Saved panorama to: {output_path}")
    else:
        print(f"Saved panorama to {output_path}")
    
    # Display result if requested
    if not args.no_display:
        # Scale down if too large
        max_display_width = 1200
        if panorama.shape[1] > max_display_width:
            scale = max_display_width / panorama.shape[1]
            display_img = cv2.resize(panorama, None, fx=scale, fy=scale)
        else:
            display_img = panorama.copy()
            
        cv2.imshow("Panorama", display_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1) 