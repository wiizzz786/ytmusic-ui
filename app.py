import os
import tempfile
import requests
from flask import Flask, jsonify, request, send_from_directory, send_file, redirect, Response, stream_with_context
from flask_cors import CORS
from ytmusicapi import YTMusic
import yt_dlp

app = Flask(__name__, static_folder='.')
CORS(app)

ytmusic = YTMusic()
DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), 'ytmusic_downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
@app.route('/index.html')
@app.route('/index.shtml')
def serve_index():
    if os.path.exists('index.html'):
        return send_from_directory('.', 'index.html')
    return "YT Music Backend Active"

@app.route('/api/home', methods=['GET'])
def get_home():
    try:
        home_data = ytmusic.get_home(limit=6)
        return jsonify({"status": "success", "data": home_data})
    except Exception as e:
        try:
            results = ytmusic.search("Top Hits 2026", limit=20)
            fallback_data = [{
                "title": "Top Trending Hits",
                "contents": results
            }]
            return jsonify({"status": "success", "data": fallback_data, "fallback": True})
        except Exception as e2:
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', 'trending')
    filter_type = request.args.get('filter', None)
    try:
        if filter_type == 'all':
            filter_type = None
        results = ytmusic.search(query, filter=filter_type, limit=30)
        return jsonify({"status": "success", "query": query, "data": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/charts', methods=['GET'])
def get_charts():
    country = request.args.get('country', 'US')
    try:
        charts = ytmusic.get_charts(country=country)
        return jsonify({"status": "success", "data": charts})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/playlist/<path:playlist_id>', methods=['GET'])
def get_playlist(playlist_id):
    try:
        playlist = ytmusic.get_playlist(playlist_id, limit=50)
        return jsonify({"status": "success", "data": playlist})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/album/<path:album_id>', methods=['GET'])
def get_album(album_id):
    try:
        album = ytmusic.get_album(album_id)
        return jsonify({"status": "success", "data": album})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/artist/<path:channel_id>', methods=['GET'])
def get_artist(channel_id):
    try:
        artist = ytmusic.get_artist(channel_id)
        return jsonify({"status": "success", "data": artist})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/explore', methods=['GET'])
def get_explore():
    try:
        categories = ytmusic.get_mood_categories()
        return jsonify({"status": "success", "data": categories})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Stream metadata endpoint
@app.route('/api/stream/<video_id>', methods=['GET'])
def stream_audio_info(video_id):
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
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Proxy live audio stream chunked directly to browser
@app.route('/api/play/<video_id>', methods=['GET'])
def play_proxy(video_id):
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

        r = requests.get(stream_url, headers=req_headers, stream=True, timeout=10)
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in r.raw.headers.items() if name.lower() not in excluded_headers]
        
        return Response(stream_with_context(r.iter_content(chunk_size=1024*64)), status=r.status_code, headers=headers)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Download endpoint
@app.route('/api/download/<video_id>', methods=['GET'])
def download_audio(video_id):
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

        req = requests.get(stream_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip()
        filename = f"{clean_title}.{ext}" if clean_title else f"{video_id}.{ext}"

        response = Response(stream_with_context(req.iter_content(chunk_size=1024*64)), content_type=req.headers.get('Content-Type', 'audio/webm'))
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        return redirect(f"https://y2mate.nu/en/v1/?url=https://www.youtube.com/watch?v={video_id}")

if __name__ == '__main__':
    print("Starting YT Music Web UI server on http://127.0.0.1:5000 ...")
    app.run(host='0.0.0.0', port=5000, debug=True)
