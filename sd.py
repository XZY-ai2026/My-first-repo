#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""黑金 3D 粒子圣诞树，带自定义名字与祝福语场景。

运行：python christmas_tree.py
自定义名字：python christmas_tree.py --name "你的名字"
自定义整句话：python christmas_tree.py --message "今天你开心了吗？"
截图：python christmas_tree.py --snapshot tree.png --time 8
导出：python christmas_tree.py --export tree.gif --duration 18 --fps 20

交互：拖动旋转，滚轮缩放，空格暂停，R 重置，S 截图，Esc 退出。
依赖：pip install pygame numpy pillow
（Python 3.14 建议：pip install pygame-ce numpy pillow）
"""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

try:
    import pygame
except ImportError as exc:
    raise SystemExit("请先安装依赖：pip install pygame numpy pillow") from exc


TAU = math.tau
SCENE_LENGTH = 6.0
TRANSITION_TIME = 1.45

# 在这里直接改名字也可以，无需加命令行参数。
DEFAULT_NAME = "阿波"
DEFAULT_SUFFIX = "有点说法"
DEFAULT_MESSAGE = "祝你开心"


def smoothstep(value):
    value = float(np.clip(value, 0.0, 1.0))
    return value * value * (3.0 - 2.0 * value)


@dataclass
class Cloud:
    """一组带独立闪烁参数的 3D 粒子。"""

    xyz: np.ndarray
    rgb: np.ndarray
    size: np.ndarray
    phase: np.ndarray
    speed: np.ndarray
    energy: np.ndarray
    twinkle: np.ndarray


def make_cloud(xyz, rgb, size, rng, energy=(0.45, 1.0), twinkle=(0.1, 0.65)):
    count = len(xyz)
    return Cloud(
        np.asarray(xyz, dtype=np.float32),
        np.asarray(rgb, dtype=np.float32),
        np.full(count, size, dtype=np.float32) if np.isscalar(size) else np.asarray(size, dtype=np.float32),
        rng.uniform(0, TAU, count).astype(np.float32),
        rng.uniform(0.7, 3.2, count).astype(np.float32),
        rng.uniform(*energy, count).astype(np.float32),
        rng.uniform(*twinkle, count).astype(np.float32),
    )


def join_clouds(clouds):
    return Cloud(*[np.concatenate([getattr(c, field) for c in clouds]) for field in (
        "xyz", "rgb", "size", "phase", "speed", "energy", "twinkle"
    )])


def golden_palette(rng, count, bright=False):
    palette = np.array([
        [255, 177, 55], [255, 207, 105], [255, 231, 168],
        [238, 137, 32], [255, 244, 214], [218, 112, 24],
    ], dtype=np.float32)
    weights = np.array([0.25, 0.25, 0.18, 0.12, 0.12, 0.08])
    colors = palette[rng.choice(len(palette), count, p=weights)].copy()
    colors *= rng.uniform(0.72, 1.18 if bright else 1.0, (count, 1))
    return np.clip(colors, 0, 255)


def build_scene(seed=20261225):
    rng = np.random.default_rng(seed)
    clouds = []
    # 七个相互重叠的锥形树冠层，形成松树枝叶的层叠轮廓。
    for layer in range(7):
        count = 680 if layer < 4 else 520
        t = rng.random(count)
        theta = rng.uniform(0, TAU, count)
        base_y = 0.72 + layer * 0.78
        base_radius = 2.72 * (1.0 - layer / 8.2) ** 1.04
        radius = base_radius * (1.0 - t) ** 0.78
        radius += rng.normal(0, 0.045, count)
        y = base_y + 1.60 * t + rng.normal(0, 0.018, count)
        xyz = np.column_stack((radius * np.cos(theta), y, radius * np.sin(theta)))
        clouds.append(make_cloud(
            xyz, golden_palette(rng, count), rng.uniform(0.55, 1.18, count), rng,
            energy=(0.26, 0.76), twinkle=(0.12, 0.62),
        ))

    # 内部较暗的粒子提供体积感，避免树冠只剩一个外壳。
    count = 1900
    t = rng.random(count)
    theta = rng.uniform(0, TAU, count)
    y = 0.8 + 6.2 * t
    max_radius = 2.50 * (1.0 - t) ** 0.92
    radius = max_radius * np.sqrt(rng.random(count)) * 0.92
    xyz = np.column_stack((radius * np.cos(theta), y, radius * np.sin(theta)))
    clouds.append(make_cloud(
        xyz, golden_palette(rng, count), rng.uniform(0.45, 0.92, count), rng,
        energy=(0.16, 0.47), twinkle=(0.08, 0.42),
    ))

    # 三条连续上升的金色螺旋灯带。
    for strand in range(3):
        count = 900
        t = np.linspace(0, 1, count) + rng.normal(0, 0.0008, count)
        t = np.clip(t, 0, 1)
        theta = TAU * (5.7 * t + strand / 3.0) + rng.normal(0, 0.018, count)
        radius = 2.76 * (1.0 - t) ** 0.91
        radius *= 0.95 + 0.045 * np.cos(TAU * 7 * t)
        radius += rng.normal(0, 0.024, count)
        y = 0.74 + 6.28 * t + rng.normal(0, 0.018, count)
        xyz = np.column_stack((radius * np.cos(theta), y, radius * np.sin(theta)))
        clouds.append(make_cloud(
            xyz, golden_palette(rng, count, True), rng.uniform(0.95, 1.62, count), rng,
            energy=(0.65, 1.30), twinkle=(0.15, 0.55),
        ))

    # 每层树枝下沿的细碎光点，让层次在旋转时更清楚。
    for layer in range(7):
        count = 210
        theta = rng.uniform(0, TAU, count)
        base_y = 0.76 + layer * 0.78
        radius = 2.72 * (1.0 - layer / 8.2) ** 1.04
        radius += 0.035 * np.sin(theta * 5 + layer) + rng.normal(0, 0.025, count)
        y = base_y + 0.06 * np.sin(theta * 3 + layer) + rng.normal(0, 0.025, count)
        xyz = np.column_stack((radius * np.cos(theta), y, radius * np.sin(theta)))
        clouds.append(make_cloud(
            xyz, golden_palette(rng, count, True), rng.uniform(0.68, 1.28, count), rng,
            energy=(0.45, 1.0), twinkle=(0.12, 0.52),
        ))

    # 少量红色与珍珠白装饰球；大部分仍保持视频中的黑金配色。
    count = 76
    t = rng.uniform(0.04, 0.89, count)
    theta = rng.uniform(0, TAU, count)
    radius = 2.70 * (1.0 - t) ** 0.91
    y = 0.78 + 6.15 * t
    xyz = np.column_stack((radius * np.cos(theta), y, radius * np.sin(theta)))
    rgb = golden_palette(rng, count, True)
    red = rng.random(count) < 0.24
    rgb[red] = np.array([255, 65, 30]) * rng.uniform(0.75, 1.1, (red.sum(), 1))
    clouds.append(make_cloud(
        xyz, rgb, rng.uniform(1.75, 2.75, count), rng,
        energy=(0.75, 1.35), twinkle=(0.08, 0.35),
    ))

    # 树干。
    count = 180
    theta = rng.uniform(0, TAU, count)
    radius = rng.uniform(0.05, 0.20, count)
    xyz = np.column_stack((radius * np.cos(theta), rng.uniform(-0.02, 0.85, count), radius * np.sin(theta)))
    rgb = np.tile(np.array([156, 87, 32]), (count, 1)) * rng.uniform(0.6, 1.2, (count, 1))
    clouds.append(make_cloud(xyz, rgb, rng.uniform(0.6, 1.1, count), rng, energy=(0.25, 0.6)))

    # 发光星球式底座：稀薄内部星云 + 明亮边缘 + 环绕轨道。
    count = 2300
    theta = rng.uniform(0, TAU, count)
    radius = 3.95 * np.sqrt(rng.random(count))
    y = rng.normal(-0.06, 0.035, count) - 0.035 * radius
    xyz = np.column_stack((radius * np.cos(theta), y, radius * np.sin(theta)))
    base_colors = golden_palette(rng, count, True)
    base_colors[:] = base_colors * 0.72 + np.array([60, 65, 80]) * 0.28
    clouds.append(make_cloud(
        xyz, base_colors, rng.uniform(0.48, 1.15, count), rng,
        energy=(0.16, 0.65), twinkle=(0.05, 0.35),
    ))

    for ring_radius, count, energy in ((3.88, 900, (0.48, 1.15)), (4.15, 420, (0.15, 0.48))):
        theta = rng.uniform(0, TAU, count)
        radius = ring_radius + rng.normal(0, 0.035 if ring_radius < 4 else 0.08, count)
        y = -0.19 + rng.normal(0, 0.025, count)
        xyz = np.column_stack((radius * np.cos(theta), y, radius * np.sin(theta)))
        clouds.append(make_cloud(
            xyz, golden_palette(rng, count, True), rng.uniform(0.65, 1.42, count), rng,
            energy=energy, twinkle=(0.04, 0.30),
        ))

    cloud = join_clouds(clouds)
    return cloud, len(cloud.xyz)


def find_chinese_font():
    """优先找常见中文字体，找不到时返回 None。"""
    names = (
        "Microsoft YaHei", "SimHei", "DengXian", "Noto Sans CJK SC",
        "Noto Sans CJK", "Source Han Sans SC", "PingFang SC",
        "WenQuanYi Zen Hei", "WenQuanYi Micro Hei", "Arial Unicode MS",
    )
    for name in names:
        path = pygame.font.match_font(name)
        if path:
            return path
    return None


def make_text_cloud(text, count, seed):
    """把中文文字采样成粒子目标点；z 方向加少量深度，避免变成薄纸片。"""
    rng = np.random.default_rng(seed)
    font_path = find_chinese_font()
    if not font_path:
        raise SystemExit("未找到中文字体。请安装微软雅黑 / 思源黑体 / Noto Sans CJK。")
    font_size = 210
    font = pygame.font.Font(font_path, font_size)
    rendered = font.render(text, True, (255, 255, 255))
    bounds = rendered.get_bounding_rect()
    if bounds.width <= 2 or bounds.height <= 2:
        raise SystemExit(f"文字无法渲染：{text}")

    # 只裁取文字有效区域，让不同长度名字都占据相近宽度。
    cropped = pygame.Surface(bounds.size, pygame.SRCALPHA)
    cropped.blit(rendered, (0, 0), bounds)
    alpha = pygame.surfarray.array_alpha(cropped)
    # surfarray 的坐标是 (x, y)，这里必须先取 x 再取 y。
    xs, ys = np.nonzero(alpha > 45)
    if len(xs) == 0:
        raise SystemExit(f"文字采样失败：{text}")

    chosen = rng.choice(len(xs), count, replace=True)
    xs = xs[chosen] + rng.normal(0, 0.55, count)
    ys = ys[chosen] + rng.normal(0, 0.55, count)
    width_world = 8.35
    pixel_scale = width_world / max(1, bounds.width)
    # 很短的文字不要被拉得过高。
    pixel_scale = min(pixel_scale, 1.55)
    center_y = 3.45
    x = (xs - bounds.width / 2) * pixel_scale
    y = center_y + (bounds.height / 2 - ys) * pixel_scale
    z = rng.normal(0, 0.10, count)
    # 轻微起伏，让文字在旋转切换时更有粒子体积感。
    y += rng.normal(0, 0.012, count)
    return np.column_stack((x, y, z)).astype(np.float32)


def put_pixels(canvas, x, y, values):
    valid = (x >= 0) & (x < canvas.shape[1]) & (y >= 0) & (y < canvas.shape[0])
    if np.any(valid):
        np.add.at(canvas, (y[valid], x[valid]), values[valid])


def splat(canvas, x, y, rgb, radius):
    """用双线性核心和高斯小核绘制粒子，避免廉价锯齿点。"""
    small = radius < 1.12
    if np.any(small):
        xs, ys, colors = x[small], y[small], rgb[small]
        x0 = np.floor(xs).astype(np.int32)
        y0 = np.floor(ys).astype(np.int32)
        fx = (xs - x0)[:, None]
        fy = (ys - y0)[:, None]
        for ox, oy, weight in (
            (0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
            (0, 1, (1 - fx) * fy), (1, 1, fx * fy),
        ):
            put_pixels(canvas, x0 + ox, y0 + oy, colors * weight)

    for selector, kernel_radius, sigma in ((radius >= 1.12, 1, 0.72), (radius >= 2.0, 2, 1.18)):
        if not np.any(selector):
            continue
        # 大粒子只由第二个核绘制，中粒子只由第一个核绘制。
        if kernel_radius == 1:
            selector = selector & (radius < 2.0)
        xs = np.rint(x[selector]).astype(np.int32)
        ys = np.rint(y[selector]).astype(np.int32)
        colors = rgb[selector]
        for oy in range(-kernel_radius, kernel_radius + 1):
            for ox in range(-kernel_radius, kernel_radius + 1):
                weight = math.exp(-(ox * ox + oy * oy) / (2 * sigma * sigma))
                put_pixels(canvas, xs + ox, ys + oy, colors * weight)


class ChristmasTree:
    def __init__(self, width=1280, height=720, custom_name=DEFAULT_NAME, name_suffix=DEFAULT_SUFFIX, message=DEFAULT_MESSAGE):
        pygame.init()
        pygame.display.set_caption("Merry Christmas · 3D Particle Tree")
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.name_text = (custom_name + name_suffix).strip() or "圣诞快乐"
        self.message_text = message.strip() or DEFAULT_MESSAGE
        self.cloud, tree_count = build_scene()
        self.tree_cloud = Cloud(*[getattr(self.cloud, field)[:tree_count] for field in (
            "xyz", "rgb", "size", "phase", "speed", "energy", "twinkle"
        )])
        self.base_cloud = Cloud(*[getattr(self.cloud, field)[tree_count:] for field in (
            "xyz", "rgb", "size", "phase", "speed", "energy", "twinkle"
        )])
        self.name_target = make_text_cloud(self.name_text, tree_count, 8128)
        self.message_target = make_text_cloud(self.message_text, tree_count, 9271)
        self.yaw = 0.30
        self.elevation = 0.16
        self.distance = 14.5
        self.running = True
        self.paused = False
        self.clock = pygame.time.Clock()
        self._font_path = self._find_script_font()
        self.resize(width, height)

    @staticmethod
    def _find_script_font():
        for name in ("Segoe Script", "Brush Script MT", "Monotype Corsiva", "Apple Chancery", "Z003", "URW Chancery L", "cursive"):
            path = pygame.font.match_font(name)
            if path:
                return path
        return None

    def resize(self, width, height):
        self.w, self.h = max(480, width), max(320, height)
        self.focal = self.h * 1.32
        self.cx, self.cy = self.w / 2, self.h * 0.55
        self.background = self._make_background()
        self.core = pygame.Surface((self.w, self.h))
        self.bright = pygame.Surface((self.w, self.h))
        self.title = self._make_title()
        self.star = self._make_star()
        self.base_aura = self._make_base_aura()

    def _make_background(self):
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        nx = (xx - self.w * 0.5) / self.w
        ny = (yy - self.h * 0.52) / self.h
        vertical = np.clip(1.0 - yy / self.h, 0, 1)
        radial = np.exp(-((nx / 0.34) ** 2 + ((ny + 0.03) / 0.55) ** 2) * 2.0)
        low_glow = np.exp(-((nx / 0.40) ** 2 + ((ny - 0.29) / 0.14) ** 2) * 2.2)
        vignette = np.clip(1.12 - 1.25 * (nx * nx + ny * ny), 0.28, 1.0)
        rgb = np.zeros((self.h, self.w, 3), dtype=np.float32)
        rgb[:] = np.array([2.0, 4.0, 10.0])
        rgb += vertical[..., None] * np.array([1.0, 2.0, 5.0])
        rgb += radial[..., None] * np.array([8.0, 4.0, 2.0])
        rgb += low_glow[..., None] * np.array([18.0, 8.0, 2.0])
        rgb *= vignette[..., None]
        surface = pygame.Surface((self.w, self.h))
        pygame.surfarray.blit_array(surface, np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2))
        return surface

    def _make_title(self):
        size = max(30, int(self.h * 0.074))
        font = pygame.font.Font(self._font_path, size) if self._font_path else pygame.font.SysFont("serif", size, italic=True)
        text = font.render("Merry Christmas", True, (255, 226, 164))
        small_font = pygame.font.SysFont("serif", max(10, int(self.h * 0.016)))
        subtitle = small_font.render("M A Y   Y O U R   D A Y S   B E   M E R R Y   &   B R I G H T", True, (172, 135, 85))
        layer = pygame.Surface((self.w, max(105, int(self.h * 0.15))), pygame.SRCALPHA)
        rect = text.get_rect(center=(self.w // 2, int(self.h * 0.045)))
        glow = text.copy()
        glow.fill((190, 105, 35, 90), special_flags=pygame.BLEND_RGBA_MULT)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1)):
            layer.blit(glow, rect.move(dx, dy))
        layer.blit(text, rect)
        sub_rect = subtitle.get_rect(center=(self.w // 2, rect.bottom + int(self.h * 0.012)))
        subtitle.set_alpha(155)
        layer.blit(subtitle, sub_rect)
        return layer

    def _make_star(self):
        side = int(max(110, self.h * 0.23))
        sprite = pygame.Surface((side, side), pygame.SRCALPHA)
        center = side // 2
        for radius in range(int(side * 0.48), 3, -2):
            p = radius / (side * 0.48)
            alpha = int(2 + 16 * (1 - p) ** 3)
            color = (255, int(105 + 105 * (1 - p)), int(25 + 100 * (1 - p)), alpha)
            pygame.draw.circle(sprite, color, (center, center), radius)
        outer, inner = side * 0.15, side * 0.064
        points = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            radius = outer if i % 2 == 0 else inner
            points.append((center + radius * math.cos(angle), center + radius * math.sin(angle)))
        pygame.draw.polygon(sprite, (255, 244, 202, 255), points)
        pygame.draw.lines(sprite, (255, 255, 239, 230), True, points, max(1, side // 130))
        pygame.draw.line(sprite, (255, 224, 147, 110), (center, int(side * 0.05)), (center, int(side * 0.95)), 1)
        pygame.draw.line(sprite, (255, 224, 147, 95), (int(side * 0.17), center), (int(side * 0.83), center), 1)
        pygame.draw.circle(sprite, (255, 255, 240, 255), (center, center), max(2, side // 45))
        return sprite

    @staticmethod
    def _make_base_aura():
        width, height = 512, 160
        yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
        x = (xx - width / 2) / (width / 2)
        y = (yy - height / 2) / (height / 2)
        radius = np.sqrt(x * x + y * y)
        mist = np.exp(-radius * radius * 3.8) * 0.18
        rim = np.exp(-((radius - 0.92) / 0.045) ** 2) * 0.70
        inner_rim = np.exp(-((radius - 0.74) / 0.12) ** 2) * 0.08
        light = (mist + rim + inner_rim) * np.clip(1.12 - radius, 0, 1)
        rgb = light[..., None] * np.array([255, 177, 76], dtype=np.float32)
        surface = pygame.Surface((width, height))
        pygame.surfarray.blit_array(surface, np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2))
        return surface

    def project(self, xyz, yaw):
        x, y, z = xyz.T
        cosine, sine = math.cos(yaw), math.sin(yaw)
        xr = cosine * x + sine * z
        zr = -sine * x + cosine * z
        yr = y - 3.25
        se, ce = math.sin(self.elevation), math.cos(self.elevation)
        depth = self.distance - (yr * se + zr * ce)
        vertical = yr * ce - zr * se
        scale = self.focal / np.maximum(depth, 0.2)
        sx = self.cx + xr * scale
        sy = self.cy - vertical * scale
        return sx, sy, depth, scale

    def project_one(self, point, yaw):
        arrays = self.project(np.asarray([point], dtype=np.float32), yaw)
        return tuple(float(a[0]) for a in arrays)

    @staticmethod
    def _counter_rotate(xyz, yaw):
        """让文字平面始终面向镜头，而圣诞树仍保持自身旋转。"""
        cosine, sine = math.cos(yaw), math.sin(yaw)
        result = np.array(xyz, dtype=np.float32, copy=True)
        # x/z 必须复制后计算，否则先写入 x 会污染后续 z 的计算。
        x = result[:, 0].copy()
        z = result[:, 2].copy()
        result[:, 0] = cosine * x - sine * z
        result[:, 2] = sine * x + cosine * z
        return result

    def scene_target(self, scene, yaw):
        if scene == 0:
            return np.array(self.tree_cloud.xyz, dtype=np.float32, copy=True)
        text = self.name_target if scene == 1 else self.message_target
        return self._counter_rotate(text, yaw)

    def scene_positions(self, t, yaw):
        """三个场景循环：圣诞树 -> 名字 -> 问候语。"""
        scene = int(t // SCENE_LENGTH) % 3
        local = t % SCENE_LENGTH
        previous_scene = (scene - 1) % 3
        current = self.scene_target(scene, yaw)

        if local < TRANSITION_TIME:
            previous = self.scene_target(previous_scene, yaw)
            global_progress = smoothstep(local / TRANSITION_TIME)
            # 每个粒子有轻微先后，转场更像金色星尘流动。
            delays = ((self.tree_cloud.phase % TAU) / TAU) * 0.45
            progress = np.clip((global_progress - delays) / 0.72, 0.0, 1.0)
            arc = np.sin(progress * math.pi)
            positions = previous * (1.0 - progress[:, None]) + current * progress[:, None]
            positions[:, 1] += arc * 0.14 * np.sin(self.tree_cloud.phase)
            text_amount = progress if previous_scene == 0 else 1.0
        else:
            positions = current
            text_amount = np.ones(len(current), dtype=np.float32)

        return positions, scene, text_amount

    def add_background_lights(self, canvas, t):
        rng = self.star_rng
        # 位置在 resize 时固定，仅亮度和雪花位置随时间变化。
        x, y = self.stars_xy.T
        phase, speed = self.stars_phase, self.stars_speed
        pulse = 0.30 + 0.70 * (0.5 + 0.5 * np.sin(phase + speed * t)) ** 2
        colors = self.stars_rgb * pulse[:, None]
        splat(canvas, x, y, colors, self.stars_size)

        count = self.snow_count
        base_x, base_y, fall_speed, drift, sizes = self.snow
        y = (base_y + fall_speed * t * self.h) % (self.h + 30) - 15
        x = (base_x + np.sin(t * 0.65 + drift) * 18 + t * 2.2) % self.w
        alpha = 0.18 + 0.42 * (0.5 + 0.5 * np.sin(drift + t * 0.8))
        rgb = np.tile(np.array([205, 218, 231]), (count, 1)) * alpha[:, None]
        splat(canvas, x, y, rgb, sizes)

    def render(self, t, yaw=None):
        yaw = self.yaw if yaw is None else yaw
        self.screen.blit(self.background, (0, 0))

        # 底座下方的柔和金色星云，粒子边缘叠在其上。
        base_x, base_y, _, base_scale = self.project_one((0, -0.16, 0), yaw)
        aura_w = max(160, int(8.3 * base_scale))
        aura_h = max(36, int(aura_w * (0.12 + 0.62 * max(0.05, math.sin(self.elevation)))))
        aura = pygame.transform.smoothscale(self.base_aura, (aura_w, aura_h))
        self.screen.blit(aura, aura.get_rect(center=(int(base_x), int(base_y))), special_flags=pygame.BLEND_RGB_ADD)

        canvas = np.zeros((self.h, self.w, 3), dtype=np.float32)
        tree_xyz, scene, text_amount = self.scene_positions(t, yaw)

        # 底座持续旋转；树冠粒子则按时间轴在树、名字、祝福语之间变形。
        for cloud, positions, boost, color_boost in (
            (self.base_cloud, self.base_cloud.xyz, 1.0, 0.0),
            (self.tree_cloud, tree_xyz, 1.0 + 0.48 * text_amount, 38.0 * text_amount),
        ):
            sx, sy, depth, scale = self.project(positions, yaw)
            visible = (depth > 1) & (sx > -8) & (sx < self.w + 8) & (sy > -8) & (sy < self.h + 8)
            twinkle = 1.0 - cloud.twinkle + cloud.twinkle * (0.5 + 0.5 * np.sin(cloud.phase + cloud.speed * t)) ** 2
            depth_light = np.clip(0.88 + 0.065 * (self.distance - depth), 0.62, 1.28)
            strength = cloud.energy * twinkle * depth_light * boost
            rgb = np.clip(cloud.rgb * strength[:, None], 0, 255)
            if np.ndim(color_boost):
                rgb = np.clip(rgb + color_boost[:, None], 0, 255)
            else:
                rgb = np.clip(rgb + color_boost, 0, 255)
            radius = cloud.size * np.clip(scale / (self.focal / self.distance), 0.72, 1.55)
            splat(canvas, sx[visible], sy[visible], rgb[visible], radius[visible])
        self.add_background_lights(canvas, t)

        rgb8 = np.clip(canvas, 0, 255).astype(np.uint8)
        pygame.surfarray.blit_array(self.core, rgb8.transpose(1, 0, 2))

        # 从高亮粒子生成两级柔光，模拟视频中温暖的光晕。
        bloom8 = np.clip((canvas - 50.0) * 0.40, 0, 255).astype(np.uint8)
        pygame.surfarray.blit_array(self.bright, bloom8.transpose(1, 0, 2))
        bloom_small = pygame.transform.smoothscale(self.bright, (max(1, self.w // 5), max(1, self.h // 5)))
        bloom = pygame.transform.smoothscale(bloom_small, (self.w, self.h))
        self.screen.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        wider = pygame.transform.smoothscale(self.bright, (max(1, self.w // 13), max(1, self.h // 13)))
        wider = pygame.transform.smoothscale(wider, (self.w, self.h))
        wider.set_alpha(95)
        self.screen.blit(wider, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        self.screen.blit(self.core, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # 顶部五角星与呼吸星芒。
        star_x, star_y, star_depth, star_scale = self.project_one((0, 7.48, 0), yaw)
        pulse = 0.94 + 0.08 * math.sin(t * 2.4)
        star_size = max(64, int(self.h * 0.17 * pulse * (14.5 / star_depth)))
        star = pygame.transform.smoothscale(self.star, (star_size, star_size))
        self.screen.blit(star, star.get_rect(center=(int(star_x), int(star_y))))
        self.screen.blit(self.title, (0, 0))
        return self.screen

    def _regenerate_sky(self):
        rng = np.random.default_rng(9917 + self.w * 3 + self.h)
        self.star_rng = rng
        count = max(110, self.w * self.h // 5200)
        self.stars_xy = np.column_stack((rng.uniform(0, self.w, count), rng.uniform(0, self.h * 0.87, count))).astype(np.float32)
        self.stars_phase = rng.uniform(0, TAU, count)
        self.stars_speed = rng.uniform(0.35, 1.5, count)
        palette = np.array([[150, 173, 210], [225, 218, 196], [255, 205, 124]], dtype=np.float32)
        self.stars_rgb = palette[rng.choice(3, count, p=[0.45, 0.40, 0.15])] * rng.uniform(0.22, 0.80, (count, 1))
        self.stars_size = rng.uniform(0.38, 1.22, count)
        self.snow_count = max(45, self.w * self.h // 10500)
        self.snow = (
            rng.uniform(0, self.w, self.snow_count), rng.uniform(0, self.h, self.snow_count),
            rng.uniform(0.018, 0.052, self.snow_count), rng.uniform(0, TAU, self.snow_count),
            rng.uniform(0.42, 1.38, self.snow_count),
        )

    def save_screenshot(self, path=None):
        if path is None:
            path = Path.cwd() / ("christmas_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png")
        pygame.image.save(self.screen, str(path))
        print(f"截图已保存：{path}")

    def run(self):
        self._regenerate_sky()
        old_size = (self.w, self.h)
        time = 0.0
        dragging = False
        last_mouse = (0, 0)
        print("\n拖动：旋转视角    滚轮：缩放    空格：暂停    R：重置    S：截图    Esc：退出\n")
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            if not self.paused:
                time += dt
                if not dragging:
                    self.yaw += dt * 0.34
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                    self.resize(*event.size)
                    self._regenerate_sky()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.yaw, self.elevation, self.distance = 0.30, 0.16, 14.5
                    elif event.key == pygame.K_s:
                        self.save_screenshot()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    dragging, last_mouse = True, event.pos
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging = False
                elif event.type == pygame.MOUSEMOTION and dragging:
                    dx, dy = event.pos[0] - last_mouse[0], event.pos[1] - last_mouse[1]
                    self.yaw += dx * 0.008
                    self.elevation = float(np.clip(self.elevation + dy * 0.0025, -0.04, 0.48))
                    last_mouse = event.pos
                elif event.type == pygame.MOUSEWHEEL:
                    self.distance = float(np.clip(self.distance - event.y * 0.65, 10.0, 21.0))
            self.render(time)
            pygame.display.flip()
        pygame.quit()


def render_snapshot(app, path, moment=2.4):
    app._regenerate_sky()
    app.render(moment)
    pygame.image.save(app.screen, str(path))
    print(f"预览图已保存：{path}")


def export_gif(app, path, duration, fps):
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("导出 GIF 需要 Pillow：pip install pillow") from exc
    app._regenerate_sky()
    total = max(1, int(duration * fps))
    frames = []
    print(f"正在渲染 {total} 帧……")
    for index in range(total):
        t = index / fps
        surface = app.render(t, yaw=0.30 + t * 0.48)
        data = pygame.image.tostring(surface, "RGB")
        image = Image.frombytes("RGB", (app.w, app.h), data)
        frames.append(image.quantize(colors=192, method=Image.Quantize.MEDIANCUT))
        if (index + 1) % max(1, fps) == 0:
            print(f"  {index + 1}/{total}")
    frames[0].save(
        str(path), save_all=True, append_images=frames[1:], loop=0,
        duration=round(1000 / fps), optimize=False, disposal=2,
    )
    print(f"GIF 已保存：{path}")


def main():
    parser = argparse.ArgumentParser(description="黑金 3D 粒子圣诞树")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--name", default=DEFAULT_NAME, help="自定义名字，例如：唐徐涛")
    parser.add_argument("--suffix", default=DEFAULT_SUFFIX, help="名字后面的文字，例如：有点说法")
    parser.add_argument("--message", default=DEFAULT_MESSAGE, help="自定义完整祝福语")
    parser.add_argument("--snapshot", type=Path, help="渲染一张 PNG 后退出")
    parser.add_argument("--time", type=float, default=2.4, help="截图时间，6-12 秒是名字场景，12-18 秒是祝福语场景")
    parser.add_argument("--export", type=Path, help="导出 GIF 后退出")
    parser.add_argument("--duration", type=float, default=18.0, help="GIF 秒数；18 秒为完整场景循环")
    parser.add_argument("--fps", type=int, default=20, help="GIF 帧率")
    args = parser.parse_args()

    if args.snapshot or args.export:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    app = ChristmasTree(args.width, args.height, args.name, args.suffix, args.message)
    try:
        if args.snapshot:
            render_snapshot(app, args.snapshot, args.time)
        elif args.export:
            export_gif(app, args.export, args.duration, args.fps)
        else:
            app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
