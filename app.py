"""
YouTube Music Web UI Backend API Server
Powered by ytmusicapi and yt-dlp
"""

import os
import re
import tempfile
import requests
from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
    send_file,
    redirect,
    Response,
    stream_with_context
)
from flask_cors import CORS
from ytmusicapi import YTMusic
import yt_dlp

app = Flask(__name__, static_folder='.')
CORS(app, resources={r"/*": {"origins": "*"}})

ytmusic = YTMusic()

DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), 'ytmusic_downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """Sanitize string for safe file naming."""
    return re.sub(r'[^\w\s\-\.]', '', filename).strip()


@app.route('/')
@app.route('/index.html')
@app.route('/index.shtml')
def serve_index():
    """Serve single-page frontend application."""
    if os.path.exists('index.html'):
        return send_from_directory('.', 'index.html')
    return jsonify({"status": "success", "message": "YT Music Backend Active"})


@app.route('/api/home', methods=['GET'])
def get_home():
    """Fetch ALL home feed recommendations and shelves."""
    try:
        # Fetch all available home shelves without capping
        home_data = ytmusic.get_home(limit=None)
        return jsonify({"status": "success", "data": home_data})
    except Exception:
        try:
            results = ytmusic.search("Top Hits 2026", limit=None)
            fallback_data = [{
                "title": "Top Trending Hits",
                "contents": results
            }]
            return jsonify({"status": "success", "data": fallback_data, "fallback": True})
        except Exception as err_fallback:
            return jsonify({"status": "error", "message": str(err_fallback)}), 500


@app.route('/api/search', methods=['GET'])
def search():
    """Search ALL available songs, albums, artists, or playlists."""
    query = request.args.get('q', 'trending').strip()
    filter_type = request.args.get('filter', None)
    if filter_type == 'all':
        filter_type = None

    try:
        # Fetch unlimited search results
        results = ytmusic.search(query, filter=filter_type, limit=None)
        return jsonify({"status": "success", "query": query, "data": results})
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/api/charts', methods=['GET'])
def get_charts():
    """Fetch complete top music charts."""
    country = request.args.get('country', 'US').upper()
    try:
        charts = ytmusic.get_charts(country=country)
        return jsonify({"status": "success", "data": charts})
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/api/playlist/<path:playlist_id>', methods=['GET'])
def get_playlist(playlist_id):
    """Fetch ALL playlist tracks and metadata."""
    try:
        playlist = ytmusic.get_playlist(playlist_id, limit=None)
        return jsonify({"status": "success", "data": playlist})
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/api/album/<path:album_id>', methods=['GET'])
def get_album(album_id):
    """Fetch all album tracks and metadata."""
    try:
        album = ytmusic.get_album(album_id)
        return jsonify({"status": "success", "data": album})
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/api/artist/<path:channel_id>', methods=['GET'])
def get_artist(channel_id):
    """Fetch artist popular tracks and discography."""
    try:
        artist = ytmusic.get_artist(channel_id)
        return jsonify({"status": "success", "data": artist})
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/api/explore', methods=['GET'])
def get_explore():
    """Fetch music mood and genre categories."""
    try:
        categories = ytmusic.get_mood_categories()
        return jsonify({"status": "success", "data": categories})
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/api/stream/<video_id>', methods=['GET'])
def stream_audio_info(video_id):
    """Fetch stream info for a track."""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True
        }
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "status": "success",
                "stream_url": f"/api/play/{video_id}",
                "title": info.get('title', 'Track'),
                "duration": info.get('duration', 0),
                "video_id": video_id
            })
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/api/play/<video_id>', methods=['GET'])
def play_proxy(video_id):
    """Proxy audio bytes directly to bypass CORS and 403 Forbidden errors."""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True
        }
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info.get('url')

        req_headers = {'User-Agent': 'Mozilla/5.0'}
        if 'Range' in request.headers:
            req_headers['Range'] = request.headers['Range']

        res = requests.get(stream_url, headers=req_headers, stream=True, timeout=10)

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [
            (name, value) for (name, value) in res.raw.headers.items()
            if name.lower() not in excluded_headers
        ]

        return Response(
            stream_with_context(res.iter_content(chunk_size=1024 * 64)),
            status=res.status_code,
            headers=headers
        )
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/api/download/<video_id>', methods=['GET'])
def download_audio(video_id):
    """Download audio track as file attachment."""
    if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
        return redirect(f"https://y2mate.nu/en/v1/?url=https://www.youtube.com/watch?v={video_id}")

    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info.get('url')
            title = info.get('title', video_id)
            ext = info.get('ext', 'webm')

        req = requests.get(stream_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        clean_title = sanitize_filename(title)
        filename = f"{clean_title}.{ext}" if clean_title else f"{video_id}.{ext}"

        response = Response(
            stream_with_context(req.iter_content(chunk_size=1024 * 64)),
            content_type=req.headers.get('Content-Type', 'audio/webm')
        )
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception:
        return redirect(f"https://y2mate.nu/en/v1/?url=https://www.youtube.com/watch?v={video_id}")


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting YT Music Web UI server on http://127.0.0.1:{port} ...")
    app.run(host='0.0.0.0', port=port, debug=True)
