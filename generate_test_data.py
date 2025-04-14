#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
from pathlib import Path
import json
import argparse

def calculate_section_parameters(img_width, num_sections, overlap_percent):
    """Calculate section parameters ensuring proper coverage with consistent overlaps."""
    # Minimum width for reliable feature detection
    min_section_width = 100
    
    # Calculate the total effective width needed
    # For n sections with overlap p%, we need:
    # W = w + (n-1)(w - p*w) where W is image width, w is section width
    # Solving for w:
    # w = W / (1 + (n-1)(1-p))
    overlap_factor = overlap_percent / 100.0
    section_width = int(img_width / (1 + (num_sections - 1) * (1 - overlap_factor)))
    
    # Calculate overlap width
    overlap_width = int(section_width * overlap_factor)
    
    # Calculate step size (distance between section starts)
    step_size = section_width - overlap_width
    
    # Verify minimum width requirement
    if section_width < min_section_width:
        raise ValueError(
            f"Section width too small ({section_width}px < {min_section_width}px). "
            f"Reduce number of sections or overlap percentage."
        )
    
    # Verify coverage
    total_coverage = step_size * (num_sections - 1) + section_width
    if total_coverage < img_width:
        # Adjust section width to ensure complete coverage
        additional_width_needed = img_width - total_coverage
        section_width += additional_width_needed
        overlap_width = int(section_width * overlap_factor)
        step_size = section_width - overlap_width
    
    return section_width, overlap_width, step_size

def validate_parameters(img_width, num_sections, overlap_percent):
    """Validate input parameters for reasonableness."""
    # Check overlap percentage
    if not 0 <= overlap_percent <= 80:
        raise ValueError("Overlap percentage must be between 0 and 80")
    
    if num_sections < 2:
        raise ValueError("Number of sections must be at least 2")
    
    # Calculate section parameters
    return calculate_section_parameters(img_width, num_sections, overlap_percent)

def split_panorama(image_path, num_sections=10, overlap_percent=40):
    """Split a panorama into overlapping sections."""
    # Read the original image
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    # Get image dimensions
    height, width = img.shape[:2]
    
    # Validate parameters and get section dimensions
    try:
        section_width, overlap_width, step_size = validate_parameters(
            width, num_sections, overlap_percent
        )
    except ValueError as e:
        print(f"Error: {e}")
        return 0
    
    # Create images directory if it doesn't exist
    output_dir = Path("images")
    try:
        output_dir.mkdir(exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory: {e}")
        return 0
    
    # Generate sections and metadata
    metadata = {
        "parameters": {
            "original_image": str(image_path),
            "width": width,
            "height": height,
            "num_sections": num_sections,
            "overlap_percent": overlap_percent,
            "section_width": section_width,
            "overlap_width": overlap_width,
            "step_size": step_size
        },
        "images": []
    }
    
    for i in range(num_sections):
        # Calculate section boundaries
        start_x = i * step_size
        end_x = min(start_x + section_width, width)
        
        # For the last section, ensure we capture until the end of the image
        if i == num_sections - 1:
            start_x = width - section_width
            
        # Extract section
        section = img[:, start_x:end_x]
        
        # Save section
        output_path = output_dir / f"section_{i:02d}.jpg"
        try:
            cv2.imwrite(str(output_path), section)
        except Exception as e:
            print(f"Error saving section {i}: {e}")
            continue
        
        # Add metadata
        metadata["images"].append({
            "filename": output_path.name,
            "position": [start_x, 0],  # Using x-offset as position
            "dimensions": {
                "width": end_x - start_x,
                "height": height
            },
            "overlap": {
                "left": i > 0,  # Has overlap on left side if not first image
                "right": i < num_sections - 1,  # Has overlap on right side if not last image
                "left_pixels": overlap_width if i > 0 else 0,
                "right_pixels": overlap_width if i < num_sections - 1 else 0
            }
        })
    
    # Save metadata
    try:
        with open(output_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"Error saving metadata: {e}")
        return 0
    
    return len(metadata["images"])

def main():
    parser = argparse.ArgumentParser(description="Split a panorama into overlapping sections")
    parser.add_argument("--input", "-i", default="original.jpg",
                      help="Input panorama image path")
    parser.add_argument("--sections", "-s", type=int, default=10,
                      help="Number of sections to split into")
    parser.add_argument("--overlap", "-o", type=int, default=40,
                      help="Overlap percentage between sections (0-80)")
    
    args = parser.parse_args()
    
    print(f"Generating {args.sections} sections with {args.overlap}% overlap...")
    try:
        num_generated = split_panorama(args.input, args.sections, args.overlap)
        if num_generated > 0:
            print(f"Successfully generated {num_generated} image sections in the 'images' directory")
        else:
            print("Failed to generate image sections")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 