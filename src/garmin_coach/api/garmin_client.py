from garminconnect import *
from garth.exc import GarthHTTPError
from requests import HTTPError

import os
from pathlib import Path

from garmin_coach.config import config


class GarminService:
    def __init__(self):
        # 使用统一配置
        self.email: str | None = config.get_email
        self.password: str | None = config.get_password
        self.tokenstore: str = config.tokenstore
        self.tokenstore_base64: str = config.tokenstore_base64
        # 是否使用中国版 Garmin Connect，默认为 False（国际版）
        self.is_cn: bool = config.is_cn

    def get_mfa(self):
        """Get MFA."""

        return input("MFA one-time code: ")

    def init_api(self):
        """初始化 Garmin API 连接"""
        import logging

        logger = logging.getLogger(__name__)

        # 如果有用户名密码，优先使用密码登录
        if self.email and self.password:
            try:
                logger.info(f"尝试使用用户名密码登录 (is_cn={self.is_cn})...")
                self.garmin = Garmin(
                    email=self.email,
                    password=self.password,
                    is_cn=self.is_cn,
                    return_on_mfa=True,
                )
                result1, result2 = self.garmin.login()

                if result1 == "needs_mfa":
                    mfa_code = self.get_mfa()
                    self.garmin.resume_login(result2, mfa_code)

                # 保存 token 供下次使用
                try:
                    self.garmin.garth.dump(self.tokenstore)
                    logger.info(f"Token 已保存到 '{self.tokenstore}'")
                except Exception as e:
                    logger.warning(f"保存 token 失败: {e}")

                return True

            except Exception as err:
                logger.error(f"用户名密码登录失败: {err}")
                return None

        # 如果没有用户名密码，尝试使用 token 登录
        try:
            logger.info("尝试使用保存的 token 登录...")
            self.garmin = Garmin(is_cn=self.is_cn)
            self.garmin.login(self.tokenstore)
            return True
        except Exception as err:
            logger.error(f"Token 登录失败: {err}")
            logger.error("请设置 EMAIL 和 PASSWORD 环境变量")
            return None

    @property
    def garminapi(self):
        return self.garmin
