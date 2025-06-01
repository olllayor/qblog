#!/usr/bin/env python3
"""
SEO Implementation Test Script
Tests the rich snippets and SEO features implementation
"""

import os
import sys

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app


def test_seo_features():
    """Test all SEO features"""
    print("🔍 Testing SEO Implementation...")

    with app.app_context():
        with app.test_request_context("/"):
            # Test 1: Check if SEO meta template exists
            try:
                from flask import render_template

                meta_content = render_template("seo_meta.html")
                print("✅ SEO meta template renders successfully")
            except Exception as e:
                print(f"❌ SEO meta template error: {e}")
                return False

            # Test 2: Check sitemap generation
            try:
                from sitemap_generator import generate_sitemap

                # Mock articles since database might not be available
                pages = generate_sitemap(app, articles=[])
                print(f"✅ Sitemap generated with {len(pages)} pages")
            except Exception as e:
                print(f"❌ Sitemap generation error: {e}")
                return False

            # Test 3: Check image files
            import os

            static_dir = os.path.join(os.path.dirname(__file__), "static")

            images_to_check = [
                "myself.jpg",
                "myself-social.jpg",
                "favicon.ico",
                "favicon.png",
            ]
            for img in images_to_check:
                if os.path.exists(os.path.join(static_dir, img)):
                    print(f"✅ Image file exists: {img}")
                else:
                    print(f"⚠️  Image file missing: {img}")

            # Test 4: Check JSON-LD structure
            if '"@context": "https://schema.org"' in meta_content:
                print("✅ JSON-LD structured data included")
            else:
                print("❌ JSON-LD structured data missing")

            # Test 5: Check Open Graph tags
            if 'property="og:' in meta_content:
                print("✅ Open Graph meta tags included")
            else:
                print("❌ Open Graph meta tags missing")

            # Test 6: Check Twitter Cards
            if 'name="twitter:' in meta_content:
                print("✅ Twitter Card meta tags included")
            else:
                print("❌ Twitter Card meta tags missing")

            print("\n🎉 SEO Implementation Test Complete!")
            print("\n📊 To verify your rich snippets:")
            print(
                "1. Test with Google Rich Results Test: https://search.google.com/test/rich-results"
            )
            print(
                "2. Facebook Sharing Debugger: https://developers.facebook.com/tools/debug/"
            )
            print("3. Twitter Card Validator: https://cards-dev.twitter.com/validator")
            print(
                "4. LinkedIn Post Inspector: https://www.linkedin.com/post-inspector/"
            )

            return True


if __name__ == "__main__":
    test_seo_features()
