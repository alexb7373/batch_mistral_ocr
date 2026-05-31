"""
Tests for image utilities module.
"""

import pytest
import base64

from src.utils.image_utils import ImageUtils, ImageFormat


class TestImageFormatEnum:
    """Tests for ImageFormat enum."""
    
    def test_all_formats_have_mime_and_extension(self):
        """Test that all formats have mime_type and extension."""
        for fmt in ImageFormat:
            assert hasattr(fmt, 'mime_type')
            assert hasattr(fmt, 'extension')
            assert fmt.mime_type.startswith('image/')
            assert fmt.extension.startswith('.')
    
    def test_specific_formats(self):
        """Test specific format values."""
        assert ImageFormat.PNG.mime_type == 'image/png'
        assert ImageFormat.PNG.extension == '.png'
        assert ImageFormat.JPEG.mime_type == 'image/jpeg'
        assert ImageFormat.JPEG.extension == '.jpeg'


class TestImageUtils:
    """Tests for ImageUtils class."""
    
    def test_detect_format_png(self):
        """Test PNG format detection."""
        # PNG magic bytes: \x89PNG\r\n\x1a\n
        png_signature = b'\x89PNG\r\n\x1a\n'
        png_base64 = base64.b64encode(png_signature + b'additional data').decode('utf-8')
        
        fmt = ImageUtils.detect_format(png_base64)
        assert fmt == ImageFormat.PNG
    
    def test_detect_format_jpeg(self):
        """Test JPEG format detection."""
        # JPEG magic bytes: \xff\xd8\xff
        jpeg_signature = b'\xff\xd8\xff'
        jpeg_base64 = base64.b64encode(jpeg_signature + b'additional data').decode('utf-8')
        
        fmt = ImageUtils.detect_format(jpeg_base64)
        assert fmt == ImageFormat.JPEG
    
    def test_detect_format_gif(self):
        """Test GIF format detection."""
        # GIF magic bytes: GIF8
        gif_signature = b'GIF8'
        gif_base64 = base64.b64encode(gif_signature + b'additional data').decode('utf-8')
        
        fmt = ImageUtils.detect_format(gif_base64)
        assert fmt == ImageFormat.GIF
    
    def test_detect_format_with_data_url_header(self):
        """Test detection with data URL header."""
        jpeg_data = base64.b64encode(b'\xff\xd8\xfftest').decode('utf-8')
        data_url = f"data:image/jpeg;base64,{jpeg_data}"
        
        fmt = ImageUtils.detect_format(data_url)
        assert fmt == ImageFormat.JPEG
    
    def test_detect_format_unknown_defaults_to_jpeg(self):
        """Test that unknown formats default to JPEG."""
        unknown_data = base64.b64encode(b'unknown data').decode('utf-8')
        
        fmt = ImageUtils.detect_format(unknown_data)
        assert fmt == ImageFormat.JPEG
    
    def test_get_mime_type(self):
        """Test getting MIME type from extension."""
        assert ImageUtils.get_mime_type('.png') == 'image/png'
        assert ImageUtils.get_mime_type('.jpeg') == 'image/jpeg'
        assert ImageUtils.get_mime_type('.jpg') == 'image/jpeg'
        assert ImageUtils.get_mime_type('.gif') == 'image/gif'
        # Unknown extension defaults to jpeg
        assert ImageUtils.get_mime_type('.unknown') == 'image/jpeg'
    
    def test_get_extension(self):
        """Test getting extension from ImageFormat."""
        assert ImageUtils.get_extension(ImageFormat.PNG) == '.png'
        assert ImageUtils.get_extension(ImageFormat.JPEG) == '.jpeg'
        assert ImageUtils.get_extension(ImageFormat.GIF) == '.gif'
    
    def test_create_data_url(self):
        """Test creating data URL."""
        mime_type = 'image/png'
        b64_data = 'base64encodeddata'
        
        data_url = ImageUtils.create_data_url(mime_type, b64_data)
        
        assert data_url == f'data:{mime_type};base64,{b64_data}'
    
    def test_decode_base64(self):
        """Test decoding base64 data."""
        original_data = b'test data'
        encoded = base64.b64encode(original_data).decode('utf-8')
        
        decoded = ImageUtils.decode_base64(encoded)
        assert decoded == original_data
    
    def test_decode_base64_with_header(self):
        """Test decoding base64 with data URL header."""
        original_data = b'test data'
        encoded = base64.b64encode(original_data).decode('utf-8')
        data_url = f'data:image/png;base64,{encoded}'
        
        decoded = ImageUtils.decode_base64(data_url)
        assert decoded == original_data
