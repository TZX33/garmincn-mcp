#!/usr/bin/env python3
"""
Garmin 数据缓存管理器

实现"本地优先"的数据获取策略：
- 历史数据：优先从本地缓存读取，不存在则从 API 获取并缓存
- 今日数据：始终从 API 获取并更新缓存（因为数据可能还在变化）
- 近期数据（可配置的"成熟窗口"内）：强制刷新以确保数据完整

目录结构：
data/cache/YYYY/MM/DD/<data_type>.json
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional


class CacheManager:
    """
    本地 JSON 缓存管理器
    """
    
    # 数据成熟窗口（天数）：这些天内的数据会强制刷新
    # 原因：Garmin 某些数据（如周均 HRV、活动卡路里校正）可能在 1-2 天后才最终确定
    MATURITY_WINDOW_DAYS = 2
    
    def __init__(self, cache_dir: str = None):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录路径，默认为项目根目录下的 data/cache
        """
        if cache_dir is None:
            # 默认使用项目根目录下的 data/cache
            project_root = Path(__file__).resolve().parent
            cache_dir = project_root / "data" / "cache"
        
        self.cache_dir = Path(cache_dir)
        self._ensure_cache_dir()
        
        # 统计信息
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls": 0,
            "forced_refreshes": 0
        }
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, date_str: str, data_type: str) -> Path:
        """
        获取指定日期和数据类型的缓存文件路径
        
        Args:
            date_str: 日期字符串，格式 YYYY-MM-DD
            data_type: 数据类型，如 'sleep', 'heart_rates', 'stress' 等
        
        Returns:
            缓存文件的完整路径
        """
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"日期格式错误: {date_str}，应为 YYYY-MM-DD")
        
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")
        
        return self.cache_dir / year / month / day / f"{data_type}.json"
    
    def _is_data_mature(self, date_str: str) -> bool:
        """
        判断指定日期的数据是否已经"成熟"（不再需要刷新）
        
        成熟的定义：日期在 MATURITY_WINDOW_DAYS 天之前
        
        Args:
            date_str: 日期字符串，格式 YYYY-MM-DD
        
        Returns:
            True 如果数据已成熟，False 如果仍在成熟窗口内
        """
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        
        days_ago = (today - date).days
        return days_ago > self.MATURITY_WINDOW_DAYS
    
    def _read_cache(self, cache_path: Path) -> Optional[dict]:
        """从缓存文件读取数据"""
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ 缓存读取失败 {cache_path}: {e}")
            return None
    
    def _write_cache(self, cache_path: Path, data: Any):
        """将数据写入缓存文件"""
        # 确保父目录存在
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except IOError as e:
            print(f"⚠️ 缓存写入失败 {cache_path}: {e}")
    
    def get_data(
        self,
        date_str: str,
        data_type: str,
        api_fetcher: Callable[[], Any],
        force_refresh: bool = False
    ) -> Optional[Any]:
        """
        获取指定日期和类型的数据（核心方法）
        
        策略：
        1. 如果 force_refresh=True，直接调 API
        2. 如果数据在"成熟窗口"内（最近 N 天），强制刷新
        3. 否则，先检查本地缓存
           - 缓存存在 -> 返回缓存
           - 缓存不存在 -> 调 API，保存缓存，返回数据
        
        Args:
            date_str: 日期字符串，格式 YYYY-MM-DD
            data_type: 数据类型标识符
            api_fetcher: 无参数的函数，调用后返回 API 数据
            force_refresh: 是否强制刷新（忽略缓存）
        
        Returns:
            数据字典，如果获取失败返回 None
        """
        cache_path = self._get_cache_path(date_str, data_type)
        
        # 判断是否需要刷新
        is_mature = self._is_data_mature(date_str)
        need_refresh = force_refresh or not is_mature
        
        # 如果数据已成熟且缓存存在，直接返回缓存
        if is_mature and not force_refresh:
            cached_data = self._read_cache(cache_path)
            if cached_data is not None:
                self.stats["cache_hits"] += 1
                return cached_data
        
        # 需要从 API 获取
        if need_refresh and not is_mature:
            self.stats["forced_refreshes"] += 1
        else:
            self.stats["cache_misses"] += 1
        
        try:
            self.stats["api_calls"] += 1
            data = api_fetcher()
            
            if data is not None:
                self._write_cache(cache_path, data)
            
            return data
        except Exception as e:
            print(f"⚠️ API 获取失败 ({date_str}/{data_type}): {e}")
            
            # 如果 API 失败但有旧缓存，尝试返回旧缓存（降级策略）
            cached_data = self._read_cache(cache_path)
            if cached_data:
                print(f"   ↳ 使用旧缓存作为 fallback")
                return cached_data
            
            return None
    
    def get_stats(self) -> dict:
        """返回缓存统计信息"""
        total = self.stats["cache_hits"] + self.stats["cache_misses"] + self.stats["forced_refreshes"]
        hit_rate = (self.stats["cache_hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 1)
        }
    
    def print_stats(self):
        """打印缓存统计摘要"""
        stats = self.get_stats()
        print(f"\n📊 缓存统计:")
        print(f"   - 缓存命中: {stats['cache_hits']} 次")
        print(f"   - 缓存未命中: {stats['cache_misses']} 次")
        print(f"   - 强制刷新: {stats['forced_refreshes']} 次")
        print(f"   - API 调用: {stats['api_calls']} 次")
        print(f"   - 命中率: {stats['hit_rate_percent']}%")
    
    def clear_cache(self, data_type: str = None, before_date: str = None):
        """
        清理缓存
        
        Args:
            data_type: 如果指定，只清理该类型的缓存；否则清理所有
            before_date: 如果指定，只清理该日期之前的缓存
        """
        import shutil
        
        if data_type is None and before_date is None:
            # 清理所有缓存
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self._ensure_cache_dir()
                print("✅ 所有缓存已清理")
        else:
            # TODO: 实现更细粒度的清理逻辑
            print("⚠️ 细粒度清理功能尚未实现")


class GarminDataFetcher:
    """
    封装 Garmin API 调用，与 CacheManager 集成
    
    提供便捷方法获取各类 Garmin 数据，自动处理缓存逻辑
    """
    
    def __init__(self, garmin_api, cache_manager: CacheManager = None):
        """
        Args:
            garmin_api: 已登录的 Garmin API 实例 (garminconnect.Garmin)
            cache_manager: 缓存管理器实例，如果不传则创建默认实例
        """
        self.api = garmin_api
        self.cache = cache_manager or CacheManager()
    
    def get_sleep_data(self, date_str: str, force_refresh: bool = False) -> Optional[dict]:
        """获取睡眠数据"""
        return self.cache.get_data(
            date_str=date_str,
            data_type="sleep",
            api_fetcher=lambda: self.api.get_sleep_data(date_str),
            force_refresh=force_refresh
        )
    
    def get_heart_rates(self, date_str: str, force_refresh: bool = False) -> Optional[dict]:
        """获取心率数据"""
        return self.cache.get_data(
            date_str=date_str,
            data_type="heart_rates",
            api_fetcher=lambda: self.api.get_heart_rates(date_str),
            force_refresh=force_refresh
        )
    
    def get_stress_data(self, date_str: str, force_refresh: bool = False) -> Optional[dict]:
        """获取压力数据"""
        return self.cache.get_data(
            date_str=date_str,
            data_type="stress",
            api_fetcher=lambda: self.api.get_stress_data(date_str),
            force_refresh=force_refresh
        )
    
    def get_hrv_data(self, date_str: str, force_refresh: bool = False) -> Optional[dict]:
        """获取 HRV 数据"""
        return self.cache.get_data(
            date_str=date_str,
            data_type="hrv",
            api_fetcher=lambda: self.api.get_hrv_data(date_str),
            force_refresh=force_refresh
        )
    
    def get_body_battery(self, date_str: str, force_refresh: bool = False) -> Optional[list]:
        """获取身体电量数据"""
        return self.cache.get_data(
            date_str=date_str,
            data_type="body_battery",
            api_fetcher=lambda: self.api.get_body_battery(date_str),
            force_refresh=force_refresh
        )
    
    def get_respiration_data(self, date_str: str, force_refresh: bool = False) -> Optional[dict]:
        """获取呼吸数据"""
        return self.cache.get_data(
            date_str=date_str,
            data_type="respiration",
            api_fetcher=lambda: self.api.get_respiration_data(date_str),
            force_refresh=force_refresh
        )
    
    def get_spo2_data(self, date_str: str, force_refresh: bool = False) -> Optional[dict]:
        """获取血氧数据"""
        return self.cache.get_data(
            date_str=date_str,
            data_type="spo2",
            api_fetcher=lambda: self.api.get_spo2_data(date_str),
            force_refresh=force_refresh
        )
    
    def get_training_readiness(self, date_str: str, force_refresh: bool = False) -> Optional[dict]:
        """获取训练准备程度"""
        return self.cache.get_data(
            date_str=date_str,
            data_type="training_readiness",
            api_fetcher=lambda: self.api.get_training_readiness(date_str),
            force_refresh=force_refresh
        )
    
    def get_stats(self) -> dict:
        """返回缓存统计"""
        return self.cache.get_stats()
    
    def print_stats(self):
        """打印缓存统计"""
        self.cache.print_stats()


# ============================================================
# 便捷函数：用于快速获取带缓存的 Fetcher
# ============================================================

def create_cached_fetcher(garmin_service) -> GarminDataFetcher:
    """
    创建一个带缓存的数据获取器
    
    用法:
        from cache_manager import create_cached_fetcher
        from mcp_server_garmincn.service.garmincn_service import GarminService
        
        service = GarminService()
        service.init_api()
        
        fetcher = create_cached_fetcher(service)
        sleep_data = fetcher.get_sleep_data("2026-02-04")
    """
    return GarminDataFetcher(garmin_service.garminapi)


if __name__ == "__main__":
    # 简单测试
    print("CacheManager 模块加载成功")
    
    cm = CacheManager()
    print(f"缓存目录: {cm.cache_dir}")
    
    # 测试路径生成
    path = cm._get_cache_path("2026-02-04", "sleep")
    print(f"示例缓存路径: {path}")
    
    # 测试成熟度判断
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    
    print(f"\n成熟度测试:")
    print(f"  今天 ({today}): 成熟={cm._is_data_mature(today)}")
    print(f"  昨天 ({yesterday}): 成熟={cm._is_data_mature(yesterday)}")
    print(f"  10天前 ({old_date}): 成熟={cm._is_data_mature(old_date)}")
