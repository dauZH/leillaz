import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_env_file():
    path = os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        if self.path == "/api/status":
            self.send_json(200, {"configured": bool(os.environ.get("OPENAI_API_KEY"))})
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/analyze":
            self.send_json(404, {"error": "Not found"})
            return
        if not os.environ.get("OPENAI_API_KEY"):
            self.send_json(503, {"error": "API key is not configured"})
            return
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            project = payload.get("project", "campus")
            language = payload.get("language", "ru")
            material = str(payload.get("material", ""))[:18000]
            answer = str(payload.get("answer", ""))[:5000]
            image = payload.get("image")
            file_data = payload.get("fileData")
            filename = str(payload.get("filename", "course.pdf"))[:160]
            instructions = {
                "ru": "Отвечай по-русски. Не выдумывай факты вне материала. Для CoursePilot создай краткий план, один вопрос экзаменатора и, если дан ответ, оцени его с точным фрагментом источника. Для CitySignal определи видимый барьер, уверенность и критичность; предложи общий осторожный обход, но не притворяйся, что знаешь карту или точное местоположение. Для RescueChef распознай продукты, пометь свежесть и сроки как неизвестные без даты/этикетки, не делай вывод о безопасности еды по фото и предложи быстрый рецепт из видимых ингредиентов.",
                "en": "Reply in English. Do not invent facts beyond the material. For CoursePilot, create a short plan and one examiner question; if an answer is provided, assess it with an exact source excerpt. For CitySignal, identify visible barriers, confidence, and severity; suggest a cautious general workaround, but do not pretend to know a map or exact location. For RescueChef, identify foods, mark freshness and expiry as unknown without dates/labels, never infer food safety from a photo, and suggest a quick recipe from visible ingredients.",
                "kk": "Қазақша жауап бер. Материалдан тыс дерек ойлап қоспа. CoursePilot үшін қысқа жоспар мен емтихан сұрағын жаса; жауап берілсе, оны бастапқы мәтіннен нақты үзіндімен бағала. CitySignal фотодағы кедергіні, сенімділікті және маңызын анықтасын; жалпы сақ айналма жол ұсынсын, бірақ нақты карта не мекенжайды білетіндей сөйлемесін. RescueChef өнімдерді анықтап, мерзімі мен балғындығын заттаңбасыз белгісіз деп көрсетсін; фотоға қарап тағам қауіпсіздігі туралы қорытынды жасамай, көрінген өнімдерден жылдам рецепт ұсынсын.",
            }.get(language, "Reply in English.")
            project_name = {"campus": "CoursePilot", "eco": "CitySignal", "build": "RescueChef AI"}.get(project, "AI project")
            text = f"Project: {project_name}\nUser material: {material}\nStudent answer: {answer}"
            content = [{"type": "input_text", "text": text}]
            if image and isinstance(image, str) and image.startswith("data:image/") and len(image) < 8_000_000:
                content.append({"type": "input_image", "image_url": image, "detail": "low"})
            if file_data and isinstance(file_data, str) and file_data.startswith("data:application/pdf;base64,") and len(file_data) < 12_000_000:
                content.append({"type": "input_file", "filename": filename, "file_data": file_data})
            if not material and len(content) == 1:
                self.send_json(400, {"error": "Add text or an image first"})
                return
            body = json.dumps({
                "model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
                "instructions": instructions,
                "input": [{"role": "user", "content": content}],
                "max_output_tokens": 700,
            }).encode("utf-8")
            request = Request("https://api.openai.com/v1/responses", data=body, headers={
                "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                "Content-Type": "application/json",
            })
            with urlopen(request, timeout=90) as response:
                result = json.loads(response.read())
            output = []
            for item in result.get("output", []):
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        output.append(part.get("text", ""))
            self.send_json(200, {"result": "\n".join(output) or "The model returned no text."})
        except HTTPError as error:
            message = error.read().decode("utf-8", "replace")[:1200]
            self.send_json(502, {"error": f"AI provider error ({error.code}): {message}"})
        except (URLError, TimeoutError) as error:
            self.send_json(502, {"error": f"Could not reach the AI provider: {error}"})
        except (ValueError, KeyError) as error:
            self.send_json(400, {"error": f"Invalid request: {error}"})

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    load_env_file()
    port = int(os.environ.get("PORT", "8000"))
    print(f"Project studio running at http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
