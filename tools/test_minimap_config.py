#!/usr/bin/env python3
"""验证 minimap 区域配置：截取小地图并保存为 test_minimap_region.png。"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.ui_interaction.screenshot import Screenshot


def main():
    shot = Screenshot()
    full = shot.capture_full_window()
    mm = shot.capture_minimap(full)
    if mm is None:
        print("未配置 minimap.region 或截取失败")
        return 1
    out = project_root / "test_minimap_region.png"
    mm.save(out)
    print(f"小地图区域已保存: {out} ({mm.size[0]}x{mm.size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
