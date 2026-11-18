#!/usr/bin/env python3
"""Download an issued Shenhuo image receipt; never call design APIs or read OAuth.

Python 3.9+ standard library. Supply original tool JSON via a private file/stdin.
Errors deliberately omit URLs, response bodies and credentials.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request

MAX_BYTES = 64 * 1024 * 1024


class DownloadError(ValueError):
    pass


def receipt_object(value):
    if not isinstance(value, dict) or value.get('isError') or value.get('error'):
        raise DownloadError('Invalid or failed tool receipt.')
    if isinstance(value.get('structuredContent'), dict):
        return receipt_object(value['structuredContent'])
    if 'download_url' in value:
        return value
    if isinstance(value.get('data'), dict):
        return receipt_object(value['data'])
    texts = [part.get('text') for part in value.get('content', [])
             if isinstance(part, dict) and part.get('type') == 'text']
    if len(texts) == 1:
        try:
            return receipt_object(json.loads(texts[0]))
        except (TypeError, json.JSONDecodeError):
            pass
    raise DownloadError('Supply the complete original get_result JSON receipt.')


def validate_receipt(value):
    receipt = receipt_object(value)
    url = receipt.get('download_url')
    filename = receipt.get('filename')
    if not isinstance(url, str) or re.search(r'\s|[\x00-\x1f\x7f]', url):
        raise DownloadError('Invalid download URL; copy the original receipt again.')
    parsed = urlsplit(url)
    # Current public transport contract. Never repair or reconstruct a ticket.
    ticket = re.fullmatch(r'/external/mcp-files/(xft_[A-Za-z0-9]+)\.[0-9a-f]{64}', parsed.path)
    if (parsed.scheme != 'https' or parsed.netloc != 'api.shenhuoai.com'
            or parsed.fragment or not ticket or ticket[1] != receipt.get('transfer_id')):
        raise DownloadError('Invalid download ticket; use a complete original receipt.')
    if receipt.get('purpose') != 'download' or not re.fullmatch(r'var_[A-Za-z0-9]+', str(receipt.get('variant_id', ''))):
        raise DownloadError('Expected an image get_result download receipt.')
    if (not isinstance(filename, str) or not filename or filename in {'.', '..'}
            or re.search(r'[/\\\x00-\x1f\x7f]', filename)
            or Path(filename).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}):
        raise DownloadError('Invalid image filename in receipt.')
    try:
        expires = datetime.fromisoformat(receipt['expires_at'].replace('Z', '+00:00'))
        if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
            raise ValueError()
    except (KeyError, AttributeError, TypeError, ValueError):
        raise DownloadError('Receipt expired or missing expiry; obtain a fresh get_result receipt.') from None
    return receipt


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def image_type(header):
    if header.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return 'image/webp'
    raise DownloadError('Response is not a supported image; no file was delivered.')


def download(value, output_dir, opener=None):
    receipt = validate_receipt(value)
    directory = Path(output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / receipt['filename']
    if target.exists() or target.is_symlink():
        raise DownloadError('Output already exists; choose a new output directory.')
    opener = opener or build_opener(NoRedirect())
    temporary = None
    try:
        # Use the exact receipt string; no URL interpolation, decoding or joining.
        request = Request(receipt['download_url'], headers={'Accept': 'image/*'})
        with opener.open(request, timeout=60) as response:
            if response.status != 200:
                raise DownloadError('Unexpected HTTP status; no file was delivered.')
            declared = response.headers.get('Content-Length')
            try:
                expected = int(declared) if declared is not None else None
            except ValueError:
                raise DownloadError('Invalid Content-Length.') from None
            if expected is not None and not 0 < expected <= MAX_BYTES:
                raise DownloadError('Invalid or oversized image response.')
            digest = hashlib.sha256()
            size = 0
            header = b''
            with tempfile.NamedTemporaryFile(dir=directory, prefix='.shenhuo-', suffix='.part', delete=False) as output:
                temporary = Path(output.name)
                while chunk := response.read(128 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise DownloadError('Image exceeds download size limit.')
                    header = (header + chunk)[:16]
                    digest.update(chunk)
                    output.write(chunk)
            if size == 0 or (expected is not None and size != expected):
                raise DownloadError('Incomplete image response; no file was delivered.')
            mime = image_type(header)
            allowed = {'image/jpeg': {'.jpg', '.jpeg'}, 'image/png': {'.png'}, 'image/webp': {'.webp'}}
            if target.suffix.lower() not in allowed[mime]:
                raise DownloadError('Image content does not match receipt filename.')
            # Atomic publication without overwriting existing output, including races.
            os.link(temporary, target)
            return {'path': str(target), 'bytes': size, 'mime_type': mime,
                    'sha256': digest.hexdigest(), 'variant_id': receipt['variant_id']}
    except HTTPError as error:
        raise DownloadError(f'HTTP {error.code}; obtain a fresh receipt for 401/403/410. Do not regenerate.') from None
    except (URLError, TimeoutError, OSError):
        raise DownloadError('Network or local file operation failed; no new delivery confirmed.') from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True, help='Private original JSON file, or - for stdin')
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    try:
        if args.receipt == '-':
            value = json.load(sys.stdin)
        else:
            with Path(args.receipt).open(encoding='utf-8') as stream:
                value = json.load(stream)
        print(json.dumps(download(value, args.output_dir), ensure_ascii=False))
    except (DownloadError, ValueError, OSError):
        # No generic exception repr: urllib and JSON errors may embed secret URLs.
        error = sys.exc_info()[1]
        message = str(error) if isinstance(error, DownloadError) else 'Cannot read a valid original JSON receipt.'
        print(message, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
