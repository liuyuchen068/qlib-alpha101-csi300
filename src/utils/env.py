import os
import logging
from dotenv import load_dotenv
from jqdatasdk import auth

logger = logging.getLogger(__name__)


def authenticate_jqdata():
    """聚宽账号认证"""
    load_dotenv()
    phone = os.getenv("JQDATASDK_PHONE")
    password = os.getenv("JQDATASDK_PASSWORD")

    if not phone or not password:
        raise ValueError("缺少 JQData 认证信息，请检查 .env 文件")

    try:
        auth(phone, password)
        logger.info("聚宽认证成功")
    except Exception as e:
        logger.error(f"聚宽认证失败: {e}")
        raise