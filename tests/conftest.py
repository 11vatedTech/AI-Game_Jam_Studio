from pathlib import Path
import pytest
from elevenvt_studio.config import StudioConfig, write_default_config
from elevenvt_studio.service import StudioService

@pytest.fixture
def service(tmp_path: Path):
    home=tmp_path/"studio-home"
    write_default_config(home)
    return StudioService(StudioConfig.load(home))
