from pathlib import Path


ENV_FILE = Path(__file__).resolve().parent / ".env"

# 缺省值：.env 中缺少对应键时使用。Web 控制台“域名与路径配置”面板会把这些键写回 .env。
DEFAULT_CONFIG = {
    "email": "",
    "password": "",
    "remix_userid": "",
    "remix_userkey": "",
    "domain": "zh.zlib.bz",
    "local_library_dir": "E:\\",
    "local_output_dir": "E:\\书单",
    "booklist_save_dir": "E:\\zlibrary_booklists",
    "booklist_use_local_index": "false",
}

ENV_KEYS = {
    "ZLIBRARY_EMAIL": "email",
    "ZLIBRARY_PASSWORD": "password",
    "ZLIBRARY_REMIX_USERID": "remix_userid",
    "ZLIBRARY_REMIX_USERKEY": "remix_userkey",
    "ZLIBRARY_DOMAIN": "domain",
    "LOCAL_LIBRARY_DIR": "local_library_dir",
    "LOCAL_OUTPUT_DIR": "local_output_dir",
    "BOOKLIST_SAVE_DIR": "booklist_save_dir",
    "BOOKLIST_USE_LOCAL_INDEX": "booklist_use_local_index",
}


def _parse_env_line(line: str):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None, None

    if stripped.startswith("export "):
        stripped = stripped[7:].strip()

    if "=" not in stripped:
        return None, None

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()

    if value and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]

    return key, value


def load_zlibrary_env(env_path: Path | None = None) -> dict[str, str]:
    """Load Z-Library credentials and app settings from a project-local .env file."""
    env_path = env_path or ENV_FILE
    config = dict(DEFAULT_CONFIG)

    if not env_path.exists():
        return config

    with env_path.open("r", encoding="utf-8") as env_file:
        for line in env_file:
            key, value = _parse_env_line(line)
            if not key:
                continue

            config_key = ENV_KEYS.get(key)
            if config_key:
                config[config_key] = value

    return config
