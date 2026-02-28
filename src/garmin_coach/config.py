import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class GarminConfig(BaseSettings):
    # API 凭证
    email: str | None = None
    password: str | None = None
    garmin_email: str | None = None
    garmin_password: str | None = None

    # Garmin 服务区域 (默认国际版 false, 中国版 true)
    is_cn: bool = False

    # 路径配置
    # 始终以当前运行目录（或者指定的环境变量）为基准来寻找 data 目录，而不是包所在的位置
    project_root: Path = Path(os.environ.get("GARMIN_COACH_ROOT", os.getcwd()))
    data_dir: Path = project_root / "data"
    db_path: Path = data_dir / "garmin.db"
    tokenstore: str = os.path.expanduser("~/.garminconnect")
    tokenstore_base64: str = os.path.expanduser("~/.garminconnect_base64")

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.environ.get("GARMIN_COACH_ROOT", os.getcwd()), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def get_email(self) -> str | None:
        return self.email or self.garmin_email

    @property
    def get_password(self) -> str | None:
        return self.password or self.garmin_password


# 全局单例
config = GarminConfig()

# 确保数据目录存在
config.data_dir.mkdir(parents=True, exist_ok=True)
