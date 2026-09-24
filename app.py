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
    Response
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
    """Fetch home feed recommendations and shelves."""
    try:
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
    """Search songs, albums, artists, or playlists."""
    query = request.args.get('q', 'trending').strip()
    filter_type = request.args.get('filter', None)
    if filter_type == 'all':
        filter_type = None

    try:
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
    """Fetch playlist tracklist and metadata."""
    try:
        playlist = ytmusic.get_playlist(playlist_id, limit=None)
        return jsonify({"status": "success", "data": playlist})
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/api/album/<path:album_id>', methods=['GET'])
def get_album(album_id):
    """Fetch album tracks and metadata."""
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
    """Extract direct high-speed audio stream URL via yt-dlp."""
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
            title = info.get('title', 'Track')
            duration = info.get('duration', 0)
            ext = info.get('ext', 'm4a')
            return jsonify({
                "status": "success",
                "stream_url": stream_url,
                "title": title,
                "duration": duration,
                "ext": ext,
                "video_id": video_id
            })
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route('/api/download/<video_id>', methods=['GET'])
def download_audio(video_id):
    """Extract direct audio download URL via yt-dlp."""
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
            if stream_url:
                return redirect(stream_url)
            
        return jsonify({"status": "error", "message": "Stream URL not found"}), 404
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting YT Music Web UI server on http://127.0.0.1:{port} ...")
    app.run(host='0.0.0.0', port=port, debug=True)
