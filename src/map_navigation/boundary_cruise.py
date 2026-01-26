"""
基于边界巡航与坐标栈回溯的刷图策略。

- 边界巡航：小地图黄点切线向量，沿墙移动。
- 回溯栈：偏离主航线前压入坐标，无怪后 pop 原路返回。
- 防卡死：角色始终在屏中央，不按点击同点判断；改用 2s 无成功移动 或 小地图连续不变 判定卡死，随机点击并清栈。
- 所有坐标均为游戏窗口逻辑坐标，考虑 Retina 2x 映射。
"""
from __future__ import annotations

import math
import random
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)


def _minimap_to_cv(img: Image.Image) -> np.ndarray:
    a = np.array(img)
    if len(a.shape) == 2:
        a = cv2.cvtColor(a, cv2.COLOR_GRAY2BGR)
    elif a.shape[2] == 3:
        a = cv2.cvtColor(a, cv2.COLOR_RGB2BGR)
    return a


def _quadrant_from_delta(dx: float, dy: float) -> str:
    """根据最近黄点相对中心的 (dx,dy) 判定象限。图像坐标 x 右 y 下。"""
    left = dx < 0
    top = dy < 0
    if top and left:
        return "tl"
    if top and not left:
        return "tr"
    if not top and left:
        return "bl"
    return "br"


def get_tangent_move_vector(
    minimap_img: Image.Image,
    last_tangent: Optional[Tuple[float, float]] = None,
    locked_direction: Optional[Tuple[float, float]] = None,
    filter_quadrant: Optional[str] = None,
) -> Optional[Tuple[float, float, float, str]]:
    """
    沿小地图黄点路径移动：取「玩家→最近黄点」的切线，选黄点延伸侧；
    若有 last_tangent 则优先延续同向，减少左右摇摆。
    若提供 filter_quadrant（tl|tr|bl|br），则仅在该象限内选择最近黄点。
    返回 (tx, ty, D_mm, quadrant)：单位切线 + 最近黄点距离（小地图像素）+ 象限 tl|tr|bl|br。
    """
    cfg = get_config()
    mm = cfg.get('minimap') or {}
    bnd = (mm.get('boundary') or {}) if isinstance(mm, dict) else {}
    lower = np.array(bnd.get('yellow_lower', [20, 100, 100]), dtype=np.uint8)
    upper = np.array(bnd.get('yellow_upper', [35, 255, 255]), dtype=np.uint8)
    min_d = float(mm.get('min_yellow_dist_px', 8))
    min_d2 = max(1e-6, min_d * min_d)

    cv_img = _minimap_to_cv(minimap_img)
    h, w = cv_img.shape[:2]
    cx, cy = w / 2.0, h / 2.0

    hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
    yellow = cv2.inRange(hsv, lower, upper)
    ys, xs = np.where(yellow > 0)
    if ys.size == 0 or xs.size == 0:
        return None

    best = None
    best_d2 = float('inf')
    for i in range(len(ys)):
        yx, yy = float(xs[i]), float(ys[i])
        d2 = (yx - cx) ** 2 + (yy - cy) ** 2
        if d2 < min_d2:
            continue
        if filter_quadrant:
            dx_test = yx - cx
            dy_test = yy - cy
            q_test = _quadrant_from_delta(dx_test, dy_test)
            if q_test != filter_quadrant:
                continue
        if d2 < best_d2:
            best_d2 = d2
            best = (yx, yy)
    if best is None:
        return None

    yx, yy = best
    dx = yx - cx
    dy = yy - cy
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return None
    logger.debug("最近黄点: 中心(%.1f,%.1f), 黄点(%.1f,%.1f), dx=%.1f, dy=%.1f, 距离=%.1f", cx, cy, yx, yy, dx, dy, L)
    ux, uy = dx / L, dy / L
    t1 = (-uy, ux)
    t2 = (uy, -ux)

    n1 = n2 = 0
    for i in range(len(ys)):
        px, py = float(xs[i]) - cx, float(ys[i]) - cy
        n1 += 1 if (px * t1[0] + py * t1[1]) > 0 else 0
        n2 += 1 if (px * t2[0] + py * t2[1]) > 0 else 0

    prefer_dir = mm.get('prefer_direction', 'auto')
    use_t1 = n1 >= n2
    
    if locked_direction is not None:
        lx, ly = locked_direction
        ll = math.hypot(lx, ly)
        if ll >= 1e-6:
            lx, ly = lx / ll, ly / ll
            d1 = lx * t1[0] + ly * t1[1]
            d2_val = lx * t2[0] + ly * t2[1]
            use_t1 = d1 >= d2_val
    elif prefer_dir == 't1':
        use_t1 = True
    elif prefer_dir == 't2':
        use_t1 = False
    elif last_tangent is not None:
        lx, ly = last_tangent
        ll = math.hypot(lx, ly)
        if ll >= 1e-6:
            lx, ly = lx / ll, ly / ll
            d1 = lx * t1[0] + ly * t1[1]
            d2_val = lx * t2[0] + ly * t2[1]
            if d1 >= 0.85:
                use_t1 = True
            elif d2_val >= 0.85:
                use_t1 = False
    
    tx, ty = t1 if use_t1 else t2
    quadrant = _quadrant_from_delta(dx, dy)
    logger.debug("象限判定: dx=%.1f, dy=%.1f -> %s", dx, dy, quadrant)
    return (tx, ty, float(L), quadrant)


def _minimap_config_for_quadrant(mm: dict, quadrant: Optional[str]) -> dict:
    """根据象限叠加 quadrants.upper / quadrants.lower 覆盖，未配置则仅用全局 mm。"""
    out = dict(mm)
    if not quadrant:
        return out
    qmap = mm.get("quadrants") or {}
    slot = "upper" if quadrant in ("tl", "tr") else "lower"
    overrides = qmap.get(slot)
    if isinstance(overrides, dict):
        for k, v in overrides.items():
            out[k] = v
    return out


def vector_to_click(
    dx: float,
    dy: float,
    window_size: Optional[Tuple[int, int]] = None,
    minimap_distance: Optional[float] = None,
    quadrant: Optional[str] = None,
) -> Tuple[int, int]:
    """
    将小地图向量转为游戏内点击坐标（逻辑坐标，Retina 2x 一致）。
    若提供 minimap_distance（小地图像素），则按 minimap_to_game_ratio 换算步长，
    并用 move_scale_min/max 限制，否则使用固定 move_scale。
    若提供 quadrant（tl|tr|bl|br），则优先使用 quadrants.upper / quadrants.lower 的覆盖配置。
    """
    cfg = get_config()
    if window_size is not None:
        w, h = window_size
    else:
        win = cfg.get("window") or {}
        w = win.get("width", 674) if isinstance(win, dict) else 674
        h = win.get("height", 316) if isinstance(win, dict) else 316
    cx, cy = w / 2.0, h / 2.0
    mm_raw = cfg.get("minimap") or {}
    mm = _minimap_config_for_quadrant(mm_raw, quadrant)
    move_scale = float(mm.get("move_scale", 50))
    ratio = mm.get("minimap_to_game_ratio")
    step_min = float(mm.get("move_scale_min", 15))
    step_max = float(mm.get("move_scale_max", 120))

    min_d_for_ratio = float(mm.get("min_distance_for_ratio", 0))
    use_ratio = (
        minimap_distance is not None
        and minimap_distance >= min_d_for_ratio
        and ratio is not None
        and float(ratio) > 0
    )
    if use_ratio:
        r = float(ratio)
        d = max(1.0, minimap_distance or 0)
        step = r * d
        step = max(step_min, min(step_max, step))
    else:
        step = move_scale

    min_d_mm = float(mm.get("min_yellow_dist_px", 5))
    close_boundary_max_step = float(mm.get("close_boundary_max_step", 0))
    thresh = mm.get("close_boundary_d_mm_threshold")
    if thresh is not None:
        close_d_mm = float(thresh)
    else:
        close_d_mm = min_d_mm * 2.0
    if minimap_distance is not None and minimap_distance < close_d_mm:
        if close_boundary_max_step > 0:
            step = min(step, close_boundary_max_step)
        else:
            step = max(step_min, min(step, move_scale * 0.8))

    gx = cx + step * dx
    gy = cy + step * dy
    gx = max(0, min(w - 1, round(gx)))
    gy = max(0, min(h - 1, round(gy)))
    return (int(gx), int(gy))


def at_backtrack_point(
    current: Tuple[int, int],
    target: Tuple[int, int],
    tolerance_px: int,
) -> bool:
    """回溯容差：到达目标附近即视为已归位。"""
    d = math.hypot(current[0] - target[0], current[1] - target[1])
    return d <= tolerance_px


def _minimap_fingerprint(img: Image.Image, size: int = 32) -> np.ndarray:
    """小地图指纹：缩放到 size x size 灰度，用于比较连续帧是否变化。"""
    a = np.array(img)
    if len(a.shape) == 3:
        a = np.mean(a, axis=2)
    a = cv2.resize(a.astype(np.float32), (size, size), interpolation=cv2.INTER_AREA)
    return a


def _minimap_changed(fp_now: np.ndarray, fp_prev: np.ndarray, threshold: float) -> bool:
    """指纹差异超过 threshold（0~1）则视为有变化。"""
    diff = np.abs(fp_now.astype(np.float64) - fp_prev.astype(np.float64))
    mean_diff = float(np.mean(diff)) / 255.0
    return mean_diff > threshold


class BoundaryCruiseDriver:
    """
    边界巡航 + 坐标栈回溯驱动。
    维护 backtrack_stack，切线移动、回溯、防卡死。
    """

    def __init__(self, screenshot=None, navigator=None):
        from src.ui_interaction.screenshot import Screenshot
        from src.map_navigation.map_navigator import MapNavigator

        self.config = get_config()
        self.screenshot = screenshot or Screenshot()
        self.navigator = navigator or MapNavigator()
        self.window_size = self.screenshot.get_window_size()

        self.backtrack_stack: List[Tuple[int, int]] = []
        self.last_move_target: Optional[Tuple[int, int]] = None
        self.last_move_time: float = 0.0
        self.backtrack_target: Optional[Tuple[int, int]] = None
        self.backtrack_since: float = 0.0
        self._last_tangent: Optional[Tuple[float, float]] = None
        self._locked_direction: Optional[Tuple[float, float]] = None
        self._same_direction_count: int = 0
        self._minimap_last_fp: Optional[np.ndarray] = None
        self._minimap_stuck_since: Optional[float] = None

        bt = self.config.get('backtrack') or {}
        self.tolerance_px = int(bt.get('tolerance_px', 40))
        self.stuck_timeout_sec = float(bt.get('stuck_timeout_sec', 2.0))
        self.stuck_same_tolerance_px = int(bt.get('stuck_same_tolerance_px', 4))
        self.escape_radius_px = int(bt.get('escape_radius_px', 80))
        self.arrive_wait_sec = float(bt.get('arrive_wait_sec', 1.0))
        self.minimap_stuck_enabled = bool(bt.get('minimap_stuck_enabled', True))
        self.minimap_stuck_diff_threshold = float(bt.get('minimap_stuck_diff_threshold', 0.02))

    def push(self, pos: Tuple[int, int]) -> None:
        self.backtrack_stack.append(pos)
        logger.debug("回溯栈 push: %s, 深度 %d", pos, len(self.backtrack_stack))

    def pop(self) -> Optional[Tuple[int, int]]:
        if not self.backtrack_stack:
            return None
        p = self.backtrack_stack.pop()
        logger.debug("回溯栈 pop: %s, 剩余 %d", p, len(self.backtrack_stack))
        return p

    def clear_stack(self) -> None:
        self.backtrack_stack.clear()
        self.backtrack_target = None
        logger.debug("回溯栈已清空")

    def _record_move(self, gx: int, gy: int) -> None:
        now = time.monotonic()
        self.last_move_target = (gx, gy)
        self.last_move_time = now

    def _dist(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def feed_minimap(self, minimap_img: Image.Image) -> None:
        """
        在每次成功巡航移动后调用，传入本次所用小地图。
        用于基于小地图变化的卡死检测：角色在动则小地图会变，卡住则几乎不变。
        仅当 minimap_stuck_enabled 且存在上一次指纹时比较。
        """
        if not self.minimap_stuck_enabled:
            return
        fp = _minimap_fingerprint(minimap_img)
        now = time.monotonic()
        if self._minimap_last_fp is None:
            self._minimap_last_fp = fp
            return
        if _minimap_changed(fp, self._minimap_last_fp, self.minimap_stuck_diff_threshold):
            self._minimap_last_fp = fp
            self._minimap_stuck_since = None
            return
        if self._minimap_stuck_since is None:
            self._minimap_stuck_since = now

    def _random_escape_click(self) -> Tuple[int, int]:
        w, h = self.window_size
        cx, cy = w // 2, h // 2
        r = self.escape_radius_px
        angle = random.uniform(0, 2 * math.pi)
        gx = int(cx + r * math.cos(angle))
        gy = int(cy + r * math.sin(angle))
        gx = max(0, min(w - 1, gx))
        gy = max(0, min(h - 1, gy))
        return (gx, gy)

    def is_stuck_cruise(self) -> bool:
        """
        巡航卡死判定（不依赖点击同点；角色始终在屏中央，同点无意义）：
        1) 超过 stuck_timeout_sec 无成功切线移动 → 卡死；
        2) 已开启小地图卡死检测且连续多次移动后小地图几乎不变 → 卡死。
        """
        now = time.monotonic()
        if self.last_move_target is not None and (now - self.last_move_time) >= self.stuck_timeout_sec:
            return True
        if self.minimap_stuck_enabled and self._minimap_stuck_since is not None:
            if (now - self._minimap_stuck_since) >= self.stuck_timeout_sec:
                return True
        return False

    def is_stuck_backtrack(self) -> bool:
        """回溯时同一目标超过 2s 未归位则视为卡死。"""
        if self.backtrack_target is None:
            return False
        return (time.monotonic() - self.backtrack_since) >= self.stuck_timeout_sec

    def trigger_escape(self) -> None:
        """防卡死：随机点击并清空回溯栈；重置切线惯性与小地图卡死状态。"""
        gx, gy = self._random_escape_click()
        self.navigator.move_to(gx, gy)
        self._record_move(gx, gy)
        self._last_tangent = None
        self._locked_direction = None
        self._same_direction_count = 0
        self._minimap_last_fp = None
        self._minimap_stuck_since = None
        self.clear_stack()
        logger.info("防卡死：随机逃逸 (%d, %d)，已清空回溯栈", gx, gy)

    def cruise_tick(self, full_image: Optional[Image.Image] = None) -> bool:
        """
        执行一次边界巡航移动。沿黄点延伸方向移动，成功返回 True；
        无黄点/无法计算切线返回 False。
        连续 3 步同向后锁定方向，避免闭环地图时左右切换。
        """
        if full_image is None:
            full_image = self.screenshot.capture_full_window()
        mm = self.screenshot.capture_minimap(full_image)
        if mm is None:
            return False
        
        mm_cfg = self.config.get('minimap') or {}
        lock_threshold = int(mm_cfg.get('direction_lock_steps', 3))
        
        out = get_tangent_move_vector(
            mm,
            last_tangent=self._last_tangent,
            locked_direction=self._locked_direction,
        )
        if out is None:
            return False
        tx, ty, d_mm, quadrant = out

        if self._last_tangent is not None:
            lx, ly = self._last_tangent
            ll = math.hypot(lx, ly)
            if ll >= 1e-6:
                lx, ly = lx / ll, ly / ll
                dot = lx * tx + ly * ty
                if dot >= 0.9:
                    self._same_direction_count += 1
                    if self._same_direction_count >= lock_threshold and self._locked_direction is None:
                        self._locked_direction = (tx, ty)
                        logger.info("方向已锁定: (%.2f, %.2f)", tx, ty)
                else:
                    self._same_direction_count = 0
                    if self._locked_direction is not None:
                        self._locked_direction = None
                        logger.info("方向锁定已解除")
        else:
            self._same_direction_count = 1
        
        self._last_tangent = (tx, ty)
        gx, gy = vector_to_click(tx, ty, self.window_size, minimap_distance=d_mm, quadrant=quadrant)
        self.navigator.move_to(gx, gy)
        self._record_move(gx, gy)
        self.feed_minimap(mm)
        mm_cfg = self.config.get('minimap') or {}
        ratio = mm_cfg.get('minimap_to_game_ratio')
        if ratio:
            step = float(ratio) * max(1.0, d_mm)
            step_min = float(mm_cfg.get('move_scale_min', 15))
            step_max = float(mm_cfg.get('move_scale_max', 120))
            step = max(step_min, min(step_max, step))
        else:
            step = float(mm_cfg.get('move_scale', 50))
        logger.debug("边界巡航: (%d, %d), 方向(%.2f,%.2f), D_mm=%.1f, 象限=%s, step=%.1f", gx, gy, tx, ty, d_mm, quadrant, step)
        return True

    def backtrack_tick(self) -> str:
        """
        执行一次回溯逻辑。
        返回 "done"（栈空且已归位）、"moving"（正在前往回溯点）、"stuck"（应触发逃逸）。
        到达判定：持续向回溯点移动满 arrive_wait_sec 即视为已归位（辅以 30–50px 容差概念，逻辑上以时间为主）。
        """
        now = time.monotonic()

        if self.is_stuck_backtrack():
            return "stuck"

        if not self.backtrack_stack and self.backtrack_target is None:
            return "done"

        if self.backtrack_target is None:
            t = self.pop()
            if t is None:
                return "done"
            self.backtrack_target = t
            self.backtrack_since = now

        elapsed = now - self.backtrack_since
        if elapsed >= self.arrive_wait_sec:
            self.backtrack_target = None
            if not self.backtrack_stack:
                return "done"
            t = self.pop()
            if t is None:
                return "done"
            self.backtrack_target = t
            self.backtrack_since = now

        self.navigator.move_to(self.backtrack_target[0], self.backtrack_target[1])
        self._record_move(self.backtrack_target[0], self.backtrack_target[1])
        logger.debug("原路回溯: (%d, %d)", self.backtrack_target[0], self.backtrack_target[1])
        return "moving"

    def get_center_position(self) -> Tuple[int, int]:
        w, h = self.window_size
        return (w // 2, h // 2)
