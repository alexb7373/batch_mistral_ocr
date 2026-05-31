"""
Configuration management for Mistral OCR Batch Processor.
"""

import os
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class AppConfig:
    """Application configuration.
    
    Attributes:
        input_dir: Directory containing PDF files to process
        output_dir: Directory to save OCR results
        api_key: Mistral API key
        diagram_models: List of models to try for diagram extraction
        regular_model: Default OCR model
        force_reprocess: Whether to reprocess existing files
        max_retries: Maximum API retry attempts
        verbose: Whether to show verbose output
    """
    input_dir: Path
    output_dir: Path
    api_key: str
    diagram_models: List[str] = field(default_factory=lambda: [
        "mistral-ocr-diagram-latest",
        "mistral-diagram-latest"
    ])
    regular_model: str = "mistral-ocr-latest"
    force_reprocess: bool = False
    max_retries: int = 3
    verbose: bool = True


def _load_local_config() -> Optional[tuple[Path, Path]]:
    """Load configuration from local config/config.py if it exists.
    
    Returns:
        tuple of (input_dir, output_dir) or None if config doesn't exist
    """
    config_path = Path("config/config.py")
    if not config_path.exists():
        return None
    
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("config_module", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        return Path(config_module.INPUT_DIR), Path(config_module.OUTPUT_DIR)
    except Exception as e:
        print(f"⚠️  Could not load config/config.py: {e}")
        return None


def _load_env_vars() -> Optional[Path]:
    """Check for .env files in various locations.
    
    Returns:
        Path to .env file if found, None otherwise
    """
    package_root = Path(__file__).resolve().parents[2]
    workspace_root = package_root.parent
    candidates = [
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        package_root / ".env",
        workspace_root / ".env",
    ]
    
    for env_path in candidates:
        if env_path.exists():
            return env_path

    return None


def _load_api_key() -> str:
    """Load Mistral API key from environment or .env file.
    
    Checks in order:
    1. Environment variable MISTRAL_API_KEY
    2. ../.env file
    3. ./.env file
    
    Returns:
        The API key
    
    Raises:
        EnvironmentError: If API key cannot be found
    """
    # Check environment variable first
    api_key = os.getenv("MISTRAL_API_KEY")
    if api_key:
        return api_key
    
    # Try loading from .env files
    env_path = _load_env_vars()
    if env_path:
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=env_path)
            api_key = os.getenv("MISTRAL_API_KEY")
            if api_key:
                return api_key
        except ImportError:
            print("⚠️  python-dotenv not installed. Using environment variables only.")
    
    raise EnvironmentError(
        "MISTRAL_API_KEY not found. "
        "Set it in your environment or create a .env file in the project root or parent directory."
    )


def load_api_key() -> str:
    """Load Mistral API key from supported environment locations."""
    return _load_api_key()


def load_config() -> AppConfig:
    """Load application configuration from multiple sources.
    
    Priority order:
    1. config/config.py
    2. Default values (pdfs/ and output/)
    
    API key sources:
    1. Environment variable
    2. ../.env
    3. ./.env
    
    Returns:
        AppConfig with all settings
    """
    # Load input/output directories
    dirs = _load_local_config()
    if dirs:
        input_dir, output_dir = dirs
        print(f"📂 Config loaded: {input_dir} -> {output_dir}")
    else:
        input_dir = Path("pdfs")
        output_dir = Path("output")
        print(f"📂 Using default directories: {input_dir} -> {output_dir}")
    
    # Load API key
    api_key = _load_api_key()
    print(f"🔑 API key loaded successfully")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return AppConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        api_key=api_key,
        diagram_models=["mistral-ocr-diagram-latest", "mistral-diagram-latest"],
        regular_model="mistral-ocr-latest",
        force_reprocess=False,
        max_retries=3,
        verbose=True
    )
