#!/usr/bin/env python3
"""Quark ID Photo - 夸克扫描王证件照生成服务"""
import sys
import argparse
import json
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from common import (
    CredentialManager, QuarkOCRClient,
    OCRResult, save_image_from_result,
)


class InvalidChoiceError(ValueError):
    """参数值不在合法范围内"""
    pass


def validate_choice(value, choices, param_name):
    """校验参数值是否在合法范围内，不合法时抛出 InvalidChoiceError"""
    if value not in choices:
        allowed = ', '.join(str(c) for c in sorted(choices, key=str))
        raise InvalidChoiceError(
            f"Invalid {param_name}: '{value}'. "
            f"Allowed: {allowed}"
        )


class IdPhotoClient(QuarkOCRClient):
    """证件照客户端 - AIGC 场景按 scene + inputConfigs 契约发请求"""

    def __init__(self, api_key: str, crop: str, style: str,
                 fuse_level: int, retouch: int, bg: str):
        super().__init__(api_key=api_key, scene="id-photo", data_type="image")
        # reqId capability 段用下划线命名（scene 是连字符），与历史请求的 reqId 保持一致
        self._function_option = "id_photo"
        self.crop = crop
        self.style = style
        self.fuse_level = fuse_level
        self.retouch = retouch
        self.bg = bg

    def _build_request_param(self, image_url=None, base64_data=None, input_configs=None):
        """构建证件照 API 请求参数（scene + inputConfigs 契约）"""
        configs = {
            "target_crop_params": self.crop,
            "style_type": self.style,
            "retouch": {"enhance": self.retouch},
        }

        # 妆容融合档位仅在非原图风格时有意义
        if self.style != "origin":
            configs["style_fuse_level"] = self.fuse_level

        # 换背景：仅在用户明确指定颜色时携带
        if self.bg and self.bg != "none":
            configs["change_background"] = {
                "need_change_background": True,
                "background_color": self.bg,
            }

        param = {
            "aiApiKey": self.api_key,
            "dataType": "image",
            "scene": self.scene,
            "inputConfigs": json.dumps(configs, ensure_ascii=False),
            "reqId": self._build_req_id(),
        }

        if base64_data:
            param["dataBase64"] = base64_data
        else:
            param["dataUrl"] = image_url

        return param


def main():
    parser = argparse.ArgumentParser(
        description="Quark ID Photo - 证件照生成（支持 URL、本地路径、BASE64）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 图片输入（三选一，必填）
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", "-u", help="图片 URL")
    group.add_argument("--path", "-p", help="本地图片文件路径")
    group.add_argument("--base64", "-b", help="BASE64 字符串")

    # 证件照参数（全部可选）
    parser.add_argument("--crop", default="1_inch",
                        help="目标裁剪规格: 1_inch / 2_inch（默认 1_inch）")
    parser.add_argument("--style", default="origin",
                        help="妆容风格: origin/baibi/hongxia/gangmai/baixi/realskin/ertong/hanshi/ziran（默认 origin）")
    parser.add_argument("--fuse-level", type=int, default=0,
                        help="妆容融合档位: 0/1/2/3（默认 0，与 --style 配合使用）")
    parser.add_argument("--retouch", type=int, default=3,
                        help="修容增强: 0/1/2/3（默认 3）")
    parser.add_argument("--bg", default=None,
                        help="背景颜色: red/white/blue，不传则 API 默认白底")

    args = parser.parse_args()

    # ---- 参数合法性校验 ----
    try:
        validate_choice(args.crop, {"1_inch", "2_inch"}, "--crop")
        validate_choice(args.style, {
            "origin", "baibi", "hongxia", "gangmai", "baixi",
            "realskin", "ertong", "hanshi", "ziran"
        }, "--style")
        validate_choice(args.fuse_level, {0, 1, 2, 3}, "--fuse-level")
        validate_choice(args.retouch, {0, 1, 2, 3}, "--retouch")
        if args.bg is not None:
            validate_choice(args.bg, {"red", "white", "blue", "none"}, "--bg")
    except InvalidChoiceError as e:
        print(OCRResult(code="INVALID_PARAM", message=str(e), data=None).to_json())
        sys.exit(1)

    # ---- 执行 API 调用 ----
    try:
        api_key = CredentialManager.load()
        with IdPhotoClient(
            api_key=api_key,
            crop=args.crop,
            style=args.style,
            fuse_level=args.fuse_level,
            retouch=args.retouch,
            bg=args.bg,
        ) as client:
            if args.base64:
                result = client.recognize(base64_data=args.base64)
            elif args.url:
                result = client.recognize(image_url=args.url)
            else:
                result = client.recognize(image_path=args.path)

        result = save_image_from_result(result)
        print(result.to_json())

    except ValueError as e:
        print(OCRResult(code="A0100", message=str(e), data=None).to_json())
        sys.exit(1)
    except Exception as e:
        print(OCRResult(code="UNKNOWN_ERROR", message=f"Unexpected error: {str(e)}", data=None).to_json())
        sys.exit(1)


if __name__ == "__main__":
    main()
