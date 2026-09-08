#!/usr/bin/env python3
# Copyright 2026 Honu Robotics
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Regenerate the shading model comparison figure on the rendering primer page.

Renders one sphere per shading model, all under identical lighting.

Figure for docs/reference/rendering-primer.md, section 1.1.3. Every sphere is the
same geometry seen by the same camera under the same three directional lights and
the same sky, so anything that differs between panels is the shading model and
nothing else.

Lighting is computed in linear space and encoded to sRGB at the end.
"""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RES = 320          # pixels per sphere panel
PAD = 26           # gap between panels
CAPTION_H = 96     # room under each sphere for its label
BG = 0.10          # linear background gray

# ---------------------------------------------------------------- environment

ZENITH = np.array([0.22, 0.38, 0.72])
HORIZON = np.array([0.60, 0.66, 0.72])
GROUND = np.array([0.16, 0.14, 0.12])

# Three directional lights. `dir` points from the surface toward the light.
LIGHTS = [
    (np.array([-0.55, 0.62, 0.56]), np.array([1.00, 0.96, 0.90]) * 3.0),   # key
    (np.array([0.75, 0.05, 0.45]), np.array([0.62, 0.72, 0.90]) * 0.55),   # fill
    (np.array([0.25, 0.35, -0.85]), np.array([0.95, 0.90, 0.85]) * 1.10),  # rim
]


def normalize(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def sky(d):
    """Radiance of the environment in direction d, shape (...,3)."""
    y = d[..., 1:2]
    up = np.clip(y, 0.0, 1.0) ** 0.6
    down = np.clip(-y, 0.0, 1.0) ** 0.5
    return np.where(y > 0, HORIZON + (ZENITH - HORIZON) * up,
                    HORIZON + (GROUND - HORIZON) * down)


def sky_prefiltered(d, roughness):
    """Sky as seen by a lobe of the given roughness: sharp when smooth, flat when rough."""
    sharp = sky(d)
    avg = (ZENITH + 2.0 * HORIZON + GROUND) * 0.25
    t = np.clip(roughness * 1.7, 0.0, 1.0)
    return sharp + (avg - sharp) * t


def ambient_irradiance(n):
    """Cheap hemispherical approximation of the sky's diffuse irradiance."""
    sky_avg = (ZENITH + HORIZON) * 0.5
    t = 0.5 + 0.5 * n[..., 1:2]
    return GROUND + (sky_avg - GROUND) * t


# ------------------------------------------------------------------- geometry

def sphere_normals():
    """Orthographic view of a unit sphere. Returns normals and a coverage mask."""
    e = np.linspace(-1.18, 1.18, RES)
    x, y = np.meshgrid(e, -e)
    r2 = x * x + y * y
    mask = r2 < 1.0
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    n = np.stack([x, y, z], axis=-1)
    n = np.where(mask[..., None], normalize(n + 1e-9), np.array([0.0, 0.0, 1.0]))
    return n, mask


# ------------------------------------------------------------- shading models
# Each returns outgoing radiance, shape (H,W,3). `n` is the surface normal and
# `v` the direction toward the eye.

def m_constant(n, v, base):
    return np.broadcast_to(base, n.shape).copy()


def _lambert_direct(n, v, kd):
    out = np.zeros_like(n)
    for ldir, lcol in LIGHTS:
        l = normalize(ldir)
        ndl = np.clip(np.sum(n * l, axis=-1, keepdims=True), 0, None)
        out += kd / np.pi * lcol * ndl
    return out


def m_lambert(n, v, kd):
    return _lambert_direct(n, v, kd) + kd * ambient_irradiance(n)


def m_phong(n, v, kd, ks, p):
    out = _lambert_direct(n, v, kd) + kd * ambient_irradiance(n)
    for ldir, lcol in LIGHTS:
        l = normalize(ldir)
        ndl = np.sum(n * l, axis=-1, keepdims=True)
        r = 2.0 * ndl * n - l                      # mirror direction of l about n
        rdv = np.clip(np.sum(r * v, axis=-1, keepdims=True), 0, None)
        out += ks * lcol * (rdv ** p) * (ndl > 0)
    return out


def m_blinn_phong(n, v, kd, ks, p):
    out = _lambert_direct(n, v, kd) + kd * ambient_irradiance(n)
    for ldir, lcol in LIGHTS:
        l = normalize(ldir)
        ndl = np.sum(n * l, axis=-1, keepdims=True)
        h = normalize(l + v)
        ndh = np.clip(np.sum(n * h, axis=-1, keepdims=True), 0, None)
        out += ks * lcol * (ndh ** p) * (ndl > 0)
    return out


def m_oren_nayar(n, v, kd, sigma):
    s2 = sigma * sigma
    A = 1.0 - 0.5 * s2 / (s2 + 0.33)
    B = 0.45 * s2 / (s2 + 0.09)
    ndv = np.clip(np.sum(n * v, axis=-1, keepdims=True), 1e-4, 1.0)
    theta_r = np.arccos(ndv)
    v_perp = normalize(v - n * ndv + 1e-9)
    out = np.zeros_like(n)
    for ldir, lcol in LIGHTS:
        l = normalize(ldir)
        ndl = np.clip(np.sum(n * l, axis=-1, keepdims=True), 0, 1.0)
        theta_i = np.arccos(np.clip(ndl, 0, 1))
        l_perp = normalize(l - n * ndl + 1e-9)
        cos_dphi = np.clip(np.sum(v_perp * l_perp, axis=-1, keepdims=True), 0, None)
        alpha = np.maximum(theta_i, theta_r)
        beta = np.minimum(theta_i, theta_r)
        f = A + B * cos_dphi * np.sin(alpha) * np.tan(beta)
        out += kd / np.pi * lcol * ndl * f
    return out + kd * ambient_irradiance(n)


def _ggx(ndh, alpha):
    a2 = alpha * alpha
    d = ndh * ndh * (a2 - 1.0) + 1.0
    return a2 / (np.pi * d * d + 1e-9)


def _smith_vis(ndl, ndv, alpha):
    """Height-correlated Smith visibility; includes the 1/(4 NdotL NdotV)."""
    a2 = alpha * alpha
    gv = ndl * np.sqrt(ndv * ndv * (1 - a2) + a2)
    gl = ndv * np.sqrt(ndl * ndl * (1 - a2) + a2)
    return 0.5 / (gv + gl + 1e-9)


def _env_brdf(ndv, roughness, f0):
    """Karis split-sum, Lazarov's analytic fit."""
    c0 = np.array([-1.0, -0.0275, -0.572, 0.022])
    c1 = np.array([1.0, 0.0425, 1.04, -0.04])
    r = roughness * c0 + c1
    a004 = np.minimum(r[0] * r[0], np.exp2(-9.28 * ndv)) * r[0] + r[1]
    a = -1.04 * a004 + r[2]
    b = 1.04 * a004 + r[3]
    return f0 * a + b


def m_cook_torrance(n, v, base, metallic, roughness):
    """glTF 2.0 Appendix B: mix(dielectric_brdf, metal_brdf, metallic)."""
    alpha = roughness * roughness
    ndv = np.clip(np.sum(n * v, axis=-1, keepdims=True), 1e-4, 1.0)
    f0_d = 0.04
    out = np.zeros_like(n)

    for ldir, lcol in LIGHTS:
        l = normalize(ldir)
        ndl = np.clip(np.sum(n * l, axis=-1, keepdims=True), 0, 1.0)
        h = normalize(l + v)
        ndh = np.clip(np.sum(n * h, axis=-1, keepdims=True), 0, 1.0)
        vdh = np.clip(np.sum(v * h, axis=-1, keepdims=True), 0, 1.0)

        spec = _ggx(ndh, alpha) * _smith_vis(ndl, ndv, alpha)
        schlick = (1.0 - vdh) ** 5

        f_d = f0_d + (1.0 - f0_d) * schlick                 # dielectric Fresnel
        dielectric = (1.0 - f_d) * base / np.pi + f_d * spec
        f_m = base + (1.0 - base) * schlick                 # conductor Fresnel
        metal = f_m * spec

        out += (dielectric + (metal - dielectric) * metallic) * lcol * ndl

    # Environment: diffuse from the hemisphere, specular from the mirror direction.
    diffuse_env = base * (1.0 - metallic) * ambient_irradiance(n) * (1.0 - f0_d)
    r_dir = normalize(2.0 * np.sum(n * v, axis=-1, keepdims=True) * n - v)
    f0 = f0_d + (base - f0_d) * metallic
    spec_env = sky_prefiltered(r_dir, roughness) * _env_brdf(ndv, roughness, f0)
    return out + diffuse_env + spec_env


def m_specular_glossiness(n, v, diffuse, specular, glossiness):
    """KHR_materials_pbrSpecularGlossiness, expressed on the same reflection model."""
    roughness = 1.0 - glossiness
    alpha = roughness * roughness
    ndv = np.clip(np.sum(n * v, axis=-1, keepdims=True), 1e-4, 1.0)
    out = np.zeros_like(n)

    for ldir, lcol in LIGHTS:
        l = normalize(ldir)
        ndl = np.clip(np.sum(n * l, axis=-1, keepdims=True), 0, 1.0)
        h = normalize(l + v)
        ndh = np.clip(np.sum(n * h, axis=-1, keepdims=True), 0, 1.0)
        vdh = np.clip(np.sum(v * h, axis=-1, keepdims=True), 0, 1.0)

        spec = _ggx(ndh, alpha) * _smith_vis(ndl, ndv, alpha)
        f = specular + (1.0 - specular) * (1.0 - vdh) ** 5
        out += ((1.0 - f) * diffuse / np.pi + f * spec) * lcol * ndl

    diffuse_env = diffuse * ambient_irradiance(n) * (1.0 - np.max(specular))
    r_dir = normalize(2.0 * np.sum(n * v, axis=-1, keepdims=True) * n - v)
    spec_env = sky_prefiltered(r_dir, roughness) * _env_brdf(ndv, roughness, specular)
    return out + diffuse_env + spec_env


# ----------------------------------------------------------------- the panels

RED = np.array([0.55, 0.075, 0.06])
GOLD = np.array([1.00, 0.766, 0.336])
WHITE = np.array([1.0, 1.0, 1.0])

PANELS = [
    ("Constant (unlit)",
     "No light of any kind enters the\ncomputation. The sphere reads as\na flat disc.",
     lambda n, v: m_constant(n, v, RED)),
    ("Lambert",
     "Shape appears, from one cosine.\nNo highlight, so the surface has\nno finish to read.",
     lambda n, v: m_lambert(n, v, RED)),
    ("Phong",
     "A highlight, placed around the\nmirror direction. Tuned by an\nexponent, not measured.",
     lambda n, v: m_phong(n, v, RED, WHITE * 0.45, 32.0)),
    ("Blinn-Phong",
     "The same highlight from the half\nvector. Nearly identical here; the\ntwo part company at grazing.",
     lambda n, v: m_blinn_phong(n, v, RED, WHITE * 0.45, 128.0)),
    ("Oren-Nayar",
     "Rough diffuse. Stays bright to the\nsilhouette instead of falling off,\nthe way the moon does.",
     lambda n, v: m_oren_nayar(n, v, RED, 0.7)),
    ("Metallic-roughness, metallic 0",
     "Same red, now with a Fresnel rim\nand the sky reflected in it. The\nhighlight is derived, not dialed.",
     lambda n, v: m_cook_torrance(n, v, RED, 0.0, 0.35)),
    ("Metallic-roughness, metallic 1",
     "Metal: no diffuse at all, and the\nreflection takes the color of the\nmetal rather than the light.",
     lambda n, v: m_cook_torrance(n, v, GOLD, 1.0, 0.35)),
    ("Specular-glossiness",
     "The panel to its left, authored\nthrough different inputs. Same\nreflection model, same pixels.",
     lambda n, v: m_specular_glossiness(n, v, np.zeros(3), GOLD, 0.65)),
]


def to_srgb(lin):
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, lin * 12.92,
                    1.055 * lin ** (1 / 2.4) - 0.055)


def main():
    n, mask = sphere_normals()
    v = np.zeros_like(n)
    v[..., 2] = 1.0

    cols, rows = 4, 2
    cw = RES + PAD
    ch = RES + CAPTION_H
    W = cols * cw + PAD
    H = rows * ch + PAD + 44

    canvas = np.full((H, W, 3), BG, dtype=np.float64)

    for i, (_, _, fn) in enumerate(PANELS):
        img = fn(n, v)
        img = np.where(mask[..., None], img, BG)
        r, c = divmod(i, cols)
        y0 = PAD + 44 + r * ch
        x0 = PAD + c * cw
        canvas[y0:y0 + RES, x0:x0 + RES] = img

    out = Image.fromarray((to_srgb(canvas) * 255 + 0.5).astype(np.uint8))
    draw = ImageDraw.Draw(out)
    fdir = "/usr/share/fonts/truetype/dejavu/"
    f_title = ImageFont.truetype(fdir + "DejaVuSans-Bold.ttf", 19)
    f_head = ImageFont.truetype(fdir + "DejaVuSans-Bold.ttf", 15)
    f_body = ImageFont.truetype(fdir + "DejaVuSans.ttf", 13)

    draw.text((PAD, 16), "One sphere per shading model. Same geometry, same three "
              "lights, same sky.", font=f_title, fill=(232, 232, 232))

    for i, (title, caption, _) in enumerate(PANELS):
        r, c = divmod(i, cols)
        y0 = PAD + 44 + r * ch
        x0 = PAD + c * cw
        draw.text((x0, y0 + RES + 9), title, font=f_head, fill=(238, 238, 238))
        draw.multiline_text((x0, y0 + RES + 31), caption, font=f_body,
                            fill=(166, 170, 176), spacing=4)

    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "reference", "images", "shading_models.png")
    dest = os.path.normpath(dest)
    out.save(dest)
    print("wrote", dest, out.size)


if __name__ == "__main__":
    main()
