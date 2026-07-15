from app.utils.config_handler import load_config
from app.utils.path_tool import get_abstract_path

chroma_config = load_config(config_path=get_abstract_path('app/config/chroma.yaml'))
prompt_config = load_config(config_path=get_abstract_path('app/config/prompt.yaml'))
