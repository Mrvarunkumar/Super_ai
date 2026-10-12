import io

TOOL = {
    "name": "look",
    "description": "See the user's screen or webcam. Call this when asked 'what's on my screen', 'look at this', 'what do you see'.",
    "parameters": {"type": "object", "properties": {
        "source": {"type": "string", "enum": ["screen", "webcam"]}}},
}


def handler(params, ctx):
    src = params.get("source", "screen")
    try:
        if src == "webcam":
            import cv2
            cap = cv2.VideoCapture(0)
            ok, frame = cap.read(); cap.release()
            if not ok: return "Could not read the webcam."
            jpeg = cv2.imencode(".jpg", frame)[1].tobytes()
        else:
            import mss
            from PIL import Image
            with mss.mss() as s:
                shot = s.grab(s.monitors[1])
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            img.thumbnail((1280, 1280))
            buf = io.BytesIO(); img.save(buf, "JPEG", quality=80); jpeg = buf.getvalue()
        ctx.send_image(jpeg, f"{src} capture")
        return f"A {src} image was just sent to you. Describe what you see."
    except ImportError as e:
        return f"Missing package: {e.name}"
    except Exception as e:
        return f"Capture failed: {e}"
