import base64
import io
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:  # pragma: no cover - graceful fallback when OCR dependency is unavailable
    RapidOCR = None


IMAGE_BASE_DIR = Path(__file__).resolve().parent
IMAGE_UPLOAD_DIR = (IMAGE_BASE_DIR / "images").resolve()
IMAGE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
IMAGE_MAX_UPLOAD_SIZE = 20 * 1024 * 1024
IMAGE_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_OCR_ENGINE = None


def sanitize_image_filename(filename: str) -> str:
    if not filename:
        raise ValueError("文件名无效")

    safe_name = Path(filename).name.strip()
    safe_name = IMAGE_INVALID_FILENAME_CHARS.sub("_", safe_name)
    safe_name = re.sub(r"\s+", " ", safe_name)

    if safe_name in {"", ".", ".."}:
        raise ValueError("文件名无效")

    extension = Path(safe_name).suffix.lower()
    if extension not in IMAGE_ALLOWED_EXTENSIONS:
        raise ValueError("仅支持 PNG、JPG、JPEG、WEBP、BMP 图片")

    if len(safe_name) > 180:
        suffix = Path(safe_name).suffix
        stem_max_length = max(1, 180 - len(suffix))
        safe_name = f"{Path(safe_name).stem[:stem_max_length]}{suffix}"

    return safe_name


def normalize_image_storage_name(filename: str) -> str:
    safe_name = Path(filename).name
    if safe_name != filename or safe_name in {"", ".", ".."}:
        raise ValueError("文件名无效")
    return safe_name


def get_image_storage_path(filename: str) -> Path:
    safe_name = normalize_image_storage_name(filename)
    file_path = (IMAGE_UPLOAD_DIR / safe_name).resolve()
    if file_path.parent != IMAGE_UPLOAD_DIR:
        raise ValueError("文件路径无效")
    return file_path


def load_image_from_bytes(content: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image)
        image.load()
        return image
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("图片内容无效，无法识别为受支持的图片格式") from exc


def load_image_from_path(file_path: Path) -> Image.Image:
    try:
        with Image.open(file_path) as image:
            normalized = ImageOps.exif_transpose(image)
            normalized.load()
            return normalized.copy()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("图片文件损坏或格式不受支持") from exc


def _safe_float(value: Any, digits: int = 4) -> float:
    return round(float(value), digits)


def _image_warning_messages(brightness: float, contrast: float, sharpness: float, width: int, height: int) -> list[str]:
    warnings = []
    if brightness < 55:
        warnings.append("图片整体偏暗，建议提升亮度或对比度。")
    elif brightness > 210:
        warnings.append("图片整体偏亮，可能存在过曝区域。")

    if contrast < 28:
        warnings.append("图片对比度较低，细节层次可能不够明显。")

    if sharpness < 12:
        warnings.append("图片清晰度偏低，可能存在模糊情况。")

    if width < 640 or height < 640:
        warnings.append("图片分辨率较低，放大后可能影响展示效果。")

    return warnings


def build_image_quality_report(image: Image.Image, file_size: int | None = None) -> dict[str, Any]:
    rgb_image = image.convert("RGB")
    grayscale = np.asarray(rgb_image.convert("L"), dtype=np.float32)
    rgb_array = np.asarray(rgb_image, dtype=np.float32)
    grad_y, grad_x = np.gradient(grayscale)
    gradient_energy = np.sqrt(np.square(grad_x) + np.square(grad_y))

    width, height = rgb_image.size
    brightness = float(grayscale.mean()) if grayscale.size else 0.0
    contrast = float(grayscale.std()) if grayscale.size else 0.0
    sharpness = float(gradient_energy.mean()) if gradient_energy.size else 0.0

    if width == height:
        orientation = "square"
    elif width > height:
        orientation = "landscape"
    else:
        orientation = "portrait"

    aspect_ratio = _safe_float(width / height, 4) if height else 0.0
    megapixels = _safe_float((width * height) / 1_000_000, 3)
    warnings = _image_warning_messages(brightness, contrast, sharpness, width, height)
    channel_means = {
        "r": _safe_float(rgb_array[:, :, 0].mean(), 2),
        "g": _safe_float(rgb_array[:, :, 1].mean(), 2),
        "b": _safe_float(rgb_array[:, :, 2].mean(), 2),
    }

    histogram_bins = list(range(0, 257, 16))
    histogram = {
        "bins": histogram_bins[:-1],
        "red": np.histogram(rgb_array[:, :, 0], bins=histogram_bins)[0].astype(int).tolist(),
        "green": np.histogram(rgb_array[:, :, 1], bins=histogram_bins)[0].astype(int).tolist(),
        "blue": np.histogram(rgb_array[:, :, 2], bins=histogram_bins)[0].astype(int).tolist(),
        "gray": np.histogram(grayscale, bins=histogram_bins)[0].astype(int).tolist(),
    }

    thumbnail = rgb_image.resize((64, 64))
    palette_image = thumbnail.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    palette_counts = palette_image.getcolors(maxcolors=5) or []
    palette = palette_image.getpalette() or []
    dominant_colors = []
    total_palette_pixels = sum(count for count, _ in palette_counts) or 1
    for count, color_index in sorted(palette_counts, key=lambda item: item[0], reverse=True)[:5]:
        palette_offset = color_index * 3
        red, green, blue = palette[palette_offset: palette_offset + 3]
        dominant_colors.append(
            {
                "hex": f"#{int(red):02X}{int(green):02X}{int(blue):02X}",
                "count": int(count),
                "percentage": _safe_float((count / total_palette_pixels) * 100, 2),
            }
        )

    return {
        "width": int(width),
        "height": int(height),
        "format": (image.format or "unknown").upper(),
        "mode": rgb_image.mode,
        "orientation": orientation,
        "aspect_ratio": aspect_ratio,
        "megapixels": megapixels,
        "brightness_score": _safe_float(brightness, 2),
        "contrast_score": _safe_float(contrast, 2),
        "sharpness_score": _safe_float(sharpness, 2),
        "channel_means": channel_means,
        "dominant_colors": dominant_colors,
        "histogram": histogram,
        "file_size": int(file_size or 0),
        "warnings": warnings,
    }


def _resolve_resize_target(image: Image.Image, target_width: int | None, target_height: int | None) -> tuple[int, int] | None:
    if not target_width and not target_height:
        return None

    original_width, original_height = image.size
    if target_width and target_height:
        return int(target_width), int(target_height)

    if target_width:
        ratio = target_width / original_width
        return int(target_width), max(1, int(round(original_height * ratio)))

    ratio = target_height / original_height
    return max(1, int(round(original_width * ratio))), int(target_height)


def apply_image_processing(
    image: Image.Image,
    *,
    grayscale: bool = False,
    binary_threshold: int | None = None,
    rotate_degrees: float = 0.0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    brightness: float = 1.0,
    contrast: float = 1.0,
    sharpen: bool = False,
    denoise: bool = False,
    crop_x: int | None = None,
    crop_y: int | None = None,
    crop_width: int | None = None,
    crop_height: int | None = None,
    target_width: int | None = None,
    target_height: int | None = None,
    preserve_aspect: bool = True,
) -> tuple[Image.Image, list[str]]:
    processed = image.copy()
    operations: list[str] = []

    if grayscale:
        processed = processed.convert("L").convert("RGB")
        operations.append("灰度化")
    else:
        processed = processed.convert("RGB")

    if flip_horizontal:
        processed = ImageOps.mirror(processed)
        operations.append("水平翻转")

    if flip_vertical:
        processed = ImageOps.flip(processed)
        operations.append("垂直翻转")

    if denoise:
        processed = processed.filter(ImageFilter.MedianFilter(size=3))
        operations.append("去噪")

    if rotate_degrees:
        processed = processed.rotate(-float(rotate_degrees), expand=True, resample=Image.Resampling.BICUBIC)
        operations.append(f"旋转 {float(rotate_degrees):g}°")

    if crop_width and crop_height:
        left = max(0, int(crop_x or 0))
        top = max(0, int(crop_y or 0))
        right = min(processed.width, left + int(crop_width))
        bottom = min(processed.height, top + int(crop_height))
        if right > left and bottom > top:
            processed = processed.crop((left, top, right, bottom))
            operations.append(f"裁剪为 {processed.width}×{processed.height}")

    resize_target = _resolve_resize_target(processed, target_width, target_height)
    if resize_target:
        if preserve_aspect:
            processed = ImageOps.contain(processed, resize_target, Image.Resampling.LANCZOS)
            operations.append(f"等比缩放至 {processed.size[0]}×{processed.size[1]}")
        else:
            processed = processed.resize(resize_target, Image.Resampling.LANCZOS)
            operations.append(f"缩放至 {resize_target[0]}×{resize_target[1]}")

    if abs(brightness - 1.0) > 1e-6:
        processed = ImageEnhance.Brightness(processed).enhance(brightness)
        operations.append(f"亮度调整为 {brightness:.2f} 倍")

    if abs(contrast - 1.0) > 1e-6:
        processed = ImageEnhance.Contrast(processed).enhance(contrast)
        operations.append(f"对比度调整为 {contrast:.2f} 倍")

    if binary_threshold is not None:
        threshold = max(0, min(255, int(binary_threshold)))
        processed = processed.convert("L").point(lambda pixel: 255 if pixel >= threshold else 0, mode="1").convert("RGB")
        operations.append(f"二值化（阈值 {threshold}）")

    if sharpen:
        processed = processed.filter(ImageFilter.SHARPEN)
        operations.append("锐化增强")

    if not operations:
        operations.append("未执行额外处理，仅生成预览")

    return processed, operations


def image_to_data_url(image: Image.Image, *, fmt: str = "PNG") -> str:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    mime = f"image/{fmt.lower()}"
    return f"data:{mime};base64,{encoded}"


def save_image_to_path(image: Image.Image, file_path: Path, *, fmt: str | None = None) -> None:
    image_format = (fmt or Path(file_path).suffix.replace(".", "") or "PNG").upper()
    if image_format == "JPG":
        image_format = "JPEG"

    save_image = image.convert("RGB") if image_format in {"JPEG", "WEBP", "BMP"} else image
    file_path.parent.mkdir(parents=True, exist_ok=True)
    save_image.save(file_path, format=image_format, quality=95)


def guess_image_mime_type(file_name: str) -> str:
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or "application/octet-stream"


def normalize_image_variant_stem(file_name: str) -> str:
    stem = Path(file_name).stem.strip() or "image"
    normalized = re.sub(r"([_-](?:edit|processed|preview|copy)\d*)+$", "", stem, flags=re.IGNORECASE).strip("._-")
    return normalized or stem or "image"


def _get_ocr_engine():
    global _OCR_ENGINE
    if RapidOCR is None:
        raise RuntimeError("OCR 依赖未安装，当前环境无法执行文字识别")
    if _OCR_ENGINE is None:
        _OCR_ENGINE = RapidOCR()
    return _OCR_ENGINE


def run_image_ocr(image: Image.Image) -> dict[str, Any]:
    ocr_engine = _get_ocr_engine()
    rgb_image = image.convert("RGB")
    buffer = io.BytesIO()
    rgb_image.save(buffer, format="PNG")

    result, elapsed = ocr_engine(buffer.getvalue())
    blocks = []
    full_text_parts = []

    for item in result or []:
        if not isinstance(item, list) or len(item) < 3:
            continue

        box_points, text, score = item
        cleaned_text = str(text or "").strip()
        if not cleaned_text:
            continue

        polygon = []
        for point in box_points or []:
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                polygon.append([float(point[0]), float(point[1])])

        blocks.append(
            {
                "text": cleaned_text,
                "score": round(float(score), 4),
                "polygon": polygon,
            }
        )
        full_text_parts.append(cleaned_text)

    average_score = (
        round(sum(item["score"] for item in blocks) / len(blocks), 4)
        if blocks
        else 0.0
    )

    structured_fields = {}
    structured_table: list[dict[str, Any]] = []
    non_empty_lines = [line for line in full_text_parts if line.strip()]

    for line in non_empty_lines:
        if "：" in line:
            key, value = line.split("：", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        key = key.strip()
        value = value.strip()
        if key and value and key not in structured_fields:
            structured_fields[key] = value

    candidate_rows = []
    for line in non_empty_lines:
        parts = [item.strip() for item in re.split(r"\t+|\s{2,}|,", line) if item.strip()]
        if len(parts) >= 2:
            candidate_rows.append(parts)

    if len(candidate_rows) >= 2:
        target_width = max(set(len(row) for row in candidate_rows), key=lambda width: [len(r) for r in candidate_rows].count(width))
        consistent_rows = [row for row in candidate_rows if len(row) == target_width]
        if len(consistent_rows) >= 2:
            headers = consistent_rows[0]
            data_rows = consistent_rows[1:]
            if any(re.search(r"[A-Za-z\u4e00-\u9fff]", item or "") for item in headers):
                structured_table = [
                    {headers[index]: row[index] for index in range(target_width)}
                    for row in data_rows
                ]
            else:
                generated_headers = [f"列{index + 1}" for index in range(target_width)]
                structured_table = [
                    {generated_headers[index]: row[index] for index in range(target_width)}
                    for row in consistent_rows
                ]

    return {
        "full_text": "\n".join(full_text_parts),
        "line_count": len(blocks),
        "average_score": average_score,
        "elapsed": [round(float(item), 4) for item in (elapsed or [])],
        "blocks": blocks,
        "structured_fields": structured_fields,
        "structured_table": structured_table,
    }


def serialize_ocr_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def deserialize_ocr_payload(payload: str | None) -> dict[str, Any] | None:
    if not payload:
        return None
    try:
        data = json.loads(payload)
        return data if isinstance(data, dict) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
