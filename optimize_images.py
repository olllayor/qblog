#!/usr/bin/env python3
"""
Image Optimization Script
Optimizes images for web performance by converting to WebP format
and resizing to appropriate dimensions
"""

import os
from pathlib import Path

from PIL import Image


def optimize_image(input_path, output_path, quality=85, max_width=1200):
    """Optimize an image by converting to WebP and resizing if needed"""
    try:
        with Image.open(input_path) as img:
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            img.save(output_path, "WEBP", quality=quality, optimize=True)

            original_size = os.path.getsize(input_path)
            new_size = os.path.getsize(output_path)
            reduction = ((original_size - new_size) / original_size) * 100

            print(f"✅ Optimized: {input_path.name}")
            print(
                f"   Original: {original_size / 1024:.1f}KB → WebP: {new_size / 1024:.1f}KB"
            )
            print(f"   Reduction: {reduction:.1f}%")

    except Exception as e:
        print(f"❌ Error optimizing {input_path}: {e}")


def create_favicon_sizes(input_path, output_dir):
    """Create multiple favicon sizes"""
    sizes = [16, 32, 48, 64, 128, 256]

    try:
        with Image.open(input_path) as img:
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")

            for size in sizes:
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                output_path = output_dir / f"favicon-{size}x{size}.png"
                resized.save(output_path, "PNG", optimize=True)
                print(
                    f"✅ Created: favicon-{size}x{size}.png ({os.path.getsize(output_path) / 1024:.1f}KB)"
                )

            ico_sizes = [(16, 16), (32, 32), (48, 48)]
            ico_images = []
            for size in ico_sizes:
                resized = img.resize(size, Image.Resampling.LANCZOS)
                ico_images.append(resized)

            ico_path = output_dir / "favicon-optimized.ico"
            ico_images[0].save(ico_path, format="ICO", sizes=ico_sizes)
            print(
                f"✅ Created: favicon-optimized.ico ({os.path.getsize(ico_path) / 1024:.1f}KB)"
            )

    except Exception as e:
        print(f"❌ Error creating favicon sizes: {e}")


def optimize_social_image(input_path, output_path, dimensions=(1200, 630)):
    """Optimize image for social media sharing"""
    try:
        with Image.open(input_path) as img:
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            img_ratio = img.width / img.height
            target_ratio = dimensions[0] / dimensions[1]

            if img_ratio > target_ratio:
                new_width = int(img.height * target_ratio)
                left = (img.width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img.height))
            else:
                new_height = int(img.width / target_ratio)
                top = (img.height - new_height) // 2
                img = img.crop((0, top, img.width, top + new_height))

            img = img.resize(dimensions, Image.Resampling.LANCZOS)

            img.save(output_path, "JPEG", quality=90, optimize=True)

            print(f"✅ Created social image: {output_path.name}")
            print(f"   Dimensions: {dimensions[0]}x{dimensions[1]}")
            print(f"   Size: {os.path.getsize(output_path) / 1024:.1f}KB")

    except Exception as e:
        print(f"❌ Error creating social image: {e}")


def main():
    static_dir = Path(__file__).parent / "static"

    print("🖼️  Starting Image Optimization...\n")

    images_to_optimize = [
        ("me.jpg", "me.webp", 85, 800),
        ("myself.png", "myself.webp", 85, 800),
        ("photo.jpg", "photo.webp", 85, 800),
    ]

    print("📦 Converting images to WebP format:")
    for input_name, output_name, quality, max_width in images_to_optimize:
        input_path = static_dir / input_name
        output_path = static_dir / output_name
        if input_path.exists():
            optimize_image(input_path, output_path, quality, max_width)
        else:
            print(f"⚠️  File not found: {input_name}")

    print("\n🎨 Creating optimized favicon sizes:")
    favicon_source = static_dir / "favicon.png"
    if favicon_source.exists():
        create_favicon_sizes(favicon_source, static_dir)
    else:
        print("⚠️  favicon.png not found")

    print("\n📱 Creating optimized social media images:")
    social_source = static_dir / "me.jpg"
    if social_source.exists():
        optimize_social_image(
            social_source, static_dir / "myself-social-optimized.jpg", (1200, 630)
        )
    else:
        print("⚠️  Source image for social media not found")

    print("\n✨ Image optimization complete!")
    print("\n📋 Next steps:")
    print("1. Update templates to use WebP images with fallbacks")
    print("2. Use the new favicon files in your HTML")
    print("3. Update social media meta tags to use optimized images")


if __name__ == "__main__":
    main()
