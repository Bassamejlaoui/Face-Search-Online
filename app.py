import os
import gradio as gr
from io import BytesIO
import zipfile
import tempfile
import random  
import json
from gradio_client import Client, handle_file
import base64
from PIL import Image
from datetime import datetime

BUY_PREMIUM = "🥇 Get Premium Token to Unlock"

STATUS_MESSAGES = {
    201: "Get a Premium Token for full link, deeper results including social profiles.", 
    301: "Invalid token! Get Premium Token using link in page"
}

BACKEND = os.getenv("BACKEND")
JS_FUNC = os.getenv("JS_FUNC")
USER = os.getenv("USER")
PASS = os.getenv("PASS")

backend = Client(BACKEND, auth=[USER, PASS])

def base64_to_image(base64_str):
    return base64.b64decode(base64_str + '=' * (-len(base64_str) % 4))

user_attempts = {}
def clear_old_entries():
    today = datetime.now().date()
    # Create a list of keys to remove
    keys_to_remove = [key for key, value in user_attempts.items() if value != today]
    # Remove old entries
    for key in keys_to_remove:
        del user_attempts[key]

def if_limited(request):
    clear_old_entries()
    user_ip = None
    if request.headers.get("x-forwarded-for"):
        user_ip = request.headers["x-forwarded-for"].split(",")[0]  # First IP in the list

    cookie_value = request.headers.get("cookie", "")
    if "user_id=" in cookie_value:
        user_id = cookie_value.split("user_id=")[1].split(";")[0]
    else:
        user_id = None
    print("##### Coming", user_id, user_ip)
    # Get today's date
    today = datetime.now().date()

    # Check if the user has already tried today (by IP or cookie)
    for key, value in user_attempts.items():
        if (key == user_ip or key == user_id) and value == today:
            return True

    # Record the attempt (store both hashed IP and hashed cookie)
    if user_ip:
        user_attempts[user_ip] = today
    if user_id:
        user_attempts[user_id] = today
    return False

def search_face(file, token_txt, request: gr.Request):
    global backend
    try:
        file1 = handle_file(file)
    except Exception as e:
        gr.Info("Please upload an image file.")
        return []

    if token == "" and if_limited(request):
        gr.Info("⏳ Wait for your next free search, or 🚀 Go Premium for deep search!", duration=12)
        return []

    country_code = ""
    if token_txt != "":
        country_code = "LL"

    try:
        result_text = backend.predict(
            file=file1,
            token=token_txt, 
            country_code=country_code,
            api_name="/search_face"
        )
    except:
        try:
            backend = Client(BACKEND, auth=[USER, PASS])
            result_text = backend.predict(
                file=file1,
                token=token_txt, 
                country_code=country_code,
                api_name="/search_face"
            )
        except:
            return []
   
    result = json.loads(result_text)
    outarray = []
    if result['status'] > 300:
        raise gr.Error(STATUS_MESSAGES[result['status']])
    
    for item in result['result']:
        image = Image.open(BytesIO(base64_to_image(item['image'])))
        outarray.append((image, item['url']))
    
    if result['status'] == 201:
        gr.Info(STATUS_MESSAGES[result['status']], duration=12)
    return outarray

def export_images(items):
    if not items:
        return None
    # Create a zip file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        url_text = ""
        i = 1
        for item in items:
            if item[1] == BUY_PREMIUM:
                continue
            with open(item[0], 'rb') as img_file:
                zip_file.writestr(f'image_{i}.jpg', img_file.read())
            url_text += f"image_{i}.jpg: {item[1]}\n"
            i += 1
        zip_file.writestr("urls.txt", url_text)
    zip_buffer.seek(0)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
        temp_file.write(zip_buffer.getvalue())
        temp_file_path = temp_file.name

    return temp_file_path

custom_css = """
caption.caption {
    user-select: text;
    cursor: text;
}
div#export_file {
    max-height: 63.39px;
}
.svelte-snayfm {
    height: auto;
}
.icon.svelte-snayfm {
    width: 48px;
    height: 48px;
}
.button-gradient {
  background: linear-gradient(45deg, #ff416c, #ff4b2b, #ff9b00, #ff416c);
  background-size: 400% 400%;
  border: none;
  padding: 14px 28px;
  font-size: 16px;
  font-weight: bold;
  color: white;
  border-radius: 10px;
  cursor: pointer;
  transition: 0.3s ease-in-out;
  animation: gradientAnimation 2s infinite linear;
  box-shadow: 0 4px 10px rgba(255, 65, 108, 0.6);
}
@keyframes gradientAnimation {
  0% { background-position: 0% 50%; }
  25% { background-position: 50% 100%; }
  50% { background-position: 100% 50%; }
  75% { background-position: 50% 0%; }
  100% { background-position: 0% 50%; }
}
.button-gradient:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 15px rgba(255, 75, 43, 0.8);
}
@keyframes labelGradientFlow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
label.svelte-i3tvor.float {
    background: linear-gradient(90deg, #555555, #333333, #555555); /* Dark gray gradient */
    background-size: 200% 200%;
    color: #f1f1f1;
    font-weight: bold;
    text-align: center;
    animation: labelGradientFlow 4s infinite ease-in-out;
    box-shadow: 0 0 6px rgba(50, 50, 50, 0.7); /* Subtle dark glow */
    transition: all 0.3s ease-in-out;
}
"""

js = """
function aff() {
const links = document.querySelectorAll('a');
const currentUrl = new URL(window.location.href);
const currentParams = currentUrl.searchParams.toString();
links.forEach(link => {
    const href = link.getAttribute('href');
    if (href && (href.startsWith('https://faceonlive.pocketsflow.com') || href.startsWith('https://faceonlive.com'))) {
        const targetUrl = new URL(href);
        // Append current page parameters to the link
        currentParams.split('&').forEach(param => {
            if (param) {
                const [key, value] = param.split('=');
                targetUrl.searchParams.set(key, value);
            }
        });
        link.setAttribute('href', targetUrl.toString());
    }
});
  return ''
}
"""

head = """
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-8YPXF4536P"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-8YPXF4536P');
</script>
"""

output = gr.Gallery(label="Search may take a few minutes.", columns=[3], object_fit="contain", height="480px", interactive=False)
col2 = gr.Column(scale=2, visible=False)

def init_ui():
    return gr.update(visible=True), gr.update(visible=False)

def search_ui():
    return gr.update(visible=False), gr.update(visible=True)

def search_face_examples(image):
    return search_face(image), gr.update(visible=False), gr.update(visible=True)

def set_url_token(request: gr.Request):
    if request and request.query_params:
        params = dict(request.query_params)
        if "ptoken" in params:
            return params["ptoken"]        
    return ""

def update_button(token):
    if token:
        return gr.update(visible=False), gr.update(value="🚀 Unlock Deep Search Now!", elem_classes="button-gradient")
    else:
        return gr.update(visible=True), gr.update(value="🔍 Free Face Search", elem_classes="")

MARKDOWN0 = """
    # Free Face Search Online - ❤️Like above if this space helps
    #### [Learn more about our Reverse Face Search](https://faceonlive.com/face-search-online)
    #### [Face Search API and Affiliate Program (50%).](https://portfolio.faceonlive.com/#face_search)
"""
MARKDOWN2 = """
### [Why Deep Search with Premium Token?](https://faceonlive.pocketsflow.com/checkout?productId=676c15b1971244a587ca07cb)  
✅ **Search Social Media, Deep Web & Uncover Hidden Profiles**  
✅ **Outperforming PimEyes + FaceCheck.ID Combined!**  
"""

MARKDOWN3_2 = """
<div align="right"><a href="https://faceonlive.pocketsflow.com/checkout?productId=677fe2b5aeced2814bc47dd1" target='_blank' style='font-size: 16px;'>Opt-Out From Search</a></div><br/>
<div align="right"><a href="https://faceseek.online" target='_blank' style='font-size: 16px;'>One more free search? 👉 FaceSeek Online</div><br/>
<div align="right"><a href="https://faceonlive.com/deepfake-detector" target='_blank' style='font-size: 16px;'>AI Generated Image & Deepfake Detector</div>
"""

PREMIUM_CHECKOUT = "https://faceonlive.pocketsflow.com/checkout?productId=676c15b1971244a587ca07cb"

with gr.Blocks(css=custom_css, head=head, delete_cache=(3600, 3600)) as demo:
    gr.Markdown(MARKDOWN0)
    with gr.Row():
        with gr.Column(scale=1) as col1:
            image = gr.Image(type='filepath', height=360)
            with gr.Row():
              with gr.Column():
                token = gr.Textbox(placeholder="(Optional) Input Premium Token here.", label="Premium Token")
              with gr.Column():
                md_premium1 = gr.Markdown(MARKDOWN2)
            gr.HTML("<div id='limit'></div>")
            with gr.Row():
                with gr.Column():
                    limit_button = gr.Button("🔍 Free Face Search")
                    face_search_button = gr.Button("Face Search", visible=False, elem_id="submit_btn")
                with gr.Column():
                    premium_search_button = gr.Button("🚀 Unlock Deep Search Now!", elem_classes="button-gradient", link=PREMIUM_CHECKOUT)
            with gr.Row():
                with gr.Column():
                    gr.Examples(['examples/1.jpg', 'examples/2.jpg'], inputs=image, cache_examples=True, fn=search_face_examples, outputs=[output, col1, col2])
                with gr.Column():
                    gr.HTML(MARKDOWN3_2)
            
        with col2.render():
            gr.Markdown("> ### **⚠️ Reminder:** Export images before refreshing the page by clicking the 'Export Images' button.")
            output.render()
            with gr.Row():
                with gr.Column():
                    md_premium2 = gr.Markdown(MARKDOWN2)
                with gr.Column():
                    export_button = gr.Button("Export Images")
                    export_file = gr.File(label="Download", elem_id="export_file")
            with gr.Row():
                with gr.Column():
                    premium_link_button = gr.Button("🚀 Unlock Deep Search Now!", elem_classes="button-gradient", link=PREMIUM_CHECKOUT)
                with gr.Column():
                    new_search_button = gr.Button("🔍 New Search")
            gr.HTML(MARKDOWN3_2)

    limit_button.click(None, js=JS_FUNC)
    face_search_button.click(search_ui, inputs=[], outputs=[col1, col2], api_name=False)
    face_search_button.click(search_face, inputs=[image, token], outputs=[output], api_name=False)
    export_button.click(export_images, inputs=[output], outputs=export_file, api_name=False)
    new_search_button.click(init_ui, inputs=[], outputs=[col1, col2], api_name=False)
    token.change(update_button, inputs=[token], outputs=[premium_search_button, limit_button])

    with gr.Row():
        with gr.Column(scale=1):
            gr.HTML('<a href="https://visitorbadge.io/status?path=https%3A%2F%2Fhuggingface.co%2Fspaces%2FFaceOnLive%2FFace-Search-Online"><img src="https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fhuggingface.co%2Fspaces%2FFaceOnLive%2FFace-Search-Online&labelColor=%23ff8a65&countColor=%2337d67a&style=flat&labelStyle=upper" /></a>')
        with gr.Column(scale=5):
            html = gr.HTML()
    demo.load(None, inputs=None, outputs=html, js=js)
    demo.load(set_url_token, inputs=None, outputs=[token])

demo.queue(api_open=False, default_concurrency_limit=8).launch(show_api=False)
