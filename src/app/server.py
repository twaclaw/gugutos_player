import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.tod import TimeOfDay, get_datetime

logger = logging.getLogger("guguto-player")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

context = {}

@app.get("/list_server_tags")
async def list_server_tags(all_caps: bool = True):
    tags = context.get('conf', {}).get('server_tags', {})
    result = []
    for tag_id, data in tags.items():
        tracks = data.get('tracks', [])
        if tracks:
            track = tracks[0]
            title = track.get('title', track.get('name', 'Unknown'))
            if all_caps:
                title = title.upper()
            image = track.get('image', '')
            if image.startswith('./'):
                image = image[1:]

            if image and not image.startswith('/'):
                image = '/' + image

            result.append({
                "id": tag_id,
                "title": title,
                "image": image
            })
    logger.info(f"Returning {len(result)} tags")
    return result

@app.post("/play/{tag_id}")
async def play(tag_id: str):
    queue = context.get('queue')
    conf = context.get('conf')
    PlayRequest = context.get('PlayRequestClass')
    track_manager = context.get('track_manager')

    if not queue or not conf or not PlayRequest or not track_manager:
        raise HTTPException(status_code=500, detail="Server not initialized correctly")

    tags = conf.get('server_tags', {})
    if tag_id not in tags:
        raise HTTPException(status_code=404, detail="Tag not found")

    tag_data = tags[tag_id]

    piece = track_manager.select_next_piece(tag_id, tag_data)

    if not piece:
        raise HTTPException(status_code=404, detail="No tracks for this tag")

    await queue.put(PlayRequest('server', piece))
    return {"status": "queued", "tag_id": tag_id}

# Mount images directory
images_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../server_images"))
if os.path.exists(images_path):
    app.mount("/images", StaticFiles(directory=images_path), name="images")

@app.get("/current_track")
async def get_current_track(all_caps: bool = True):
    # mock_track = {
    #     "name": "The Four Seasons: Spring",
    #     "artist": "Antonio Vivaldi",
    #     "image": "https://i.scdn.co/image/ab67616d0000b2734121faee8df82c526cbab2be"
    # }

    # if all_caps:
    #     mock_track["name"] = mock_track["name"].upper()
    #     mock_track["artist"] = mock_track["artist"].upper()

    # return mock_track

    track = context.get('current_track', {}).copy()
    if all_caps:
        if 'name' in track:
            track['name'] = track['name'].upper()
        if 'artist' in track:
            track['artist'] = track['artist'].upper()
    return track

@app.get("/current_time")
async def get_current_time(lang: str = "ES", all_caps: bool = True) -> TimeOfDay:
    if lang not in ["ES", "LT", "EN", "DE"]:
        lang = "ES"
    return get_datetime(all_caps=all_caps, language=lang)

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/out"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="ui")

async def run_server(queue, conf, play_request_cls, current_track_dict, track_manager):
    context['queue'] = queue
    context['conf'] = conf
    context['PlayRequestClass'] = play_request_cls
    context['current_track'] = current_track_dict
    context['track_manager'] = track_manager

    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
